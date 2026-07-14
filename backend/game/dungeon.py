"""The Substrate — a Zork-style explorable dungeon beneath Nexus City.

Each floor is a seeded room *graph* on a lattice: rooms with compass exits
(flavor-labeled), fog-of-war (you only know rooms you've visited and doorways
you've seen), hidden rooms behind concealed exits (found via Search + Wit),
and floor-scoped puzzles. Moving through an exit is a single action.

Descent (per design): boss floors (3/6/9) — the boss is camped in the
stairwell room and must fall. Other floors — the stairs are locked by the
floor's puzzle (a keycard hidden somewhere, or two generators to power up),
and a miniboss guards an optional hoard instead.

Enemies are room-based and telegraphed: uncleared threats leak hints through
doorways ("something is ticking beyond the east door"). Cleared rooms stay
cleared. Combat/loot/status engines are unchanged — this module only owns
topology, movement, and puzzle state.
"""

import random as _random

from game import combat, data, inventory
from game.errors import GameError

ENTRANCE_DISTRICT = "the_shallows"
MAX_FLOOR = 9
ENTER_ENERGY_COST = 10
ENTER_MINUTES = 30
MOVE_MINUTES = 5
SEARCH_MINUTES = 10
DEFEAT_CREDIT_LOSS = 0.15
REST_HEAL_FRACTION = 0.4
SEARCH_DC = 7  # wit + d6 must reach this to spot a concealed exit
RECRUIT_AFFECTION = 25  # a friend (stage threshold) will follow you down

DIRS = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0)}
OPPOSITE = {"n": "s", "s": "n", "e": "w", "w": "e"}
DIR_WORD = {"n": "north", "s": "south", "e": "east", "w": "west"}

BOSS_BY_FLOOR = {3: "chrome_contessa", 6: "neon_seraph", 9: "substrate_empress"}
MINIBOSSES = ["warden_lyss", "overclock_queen", "spore_matriarch"]

# Premium loot pool for hidden caches and miniboss hoards.
PREMIUM_LOOT = [
    "surge_gem",
    "sage_gem",
    "fortune_gem",
    "singing_crystal",
    "voidglass_edge",
    "band_of_the_deep",
    "nano_patch",
]


def _tier_for(floor):
    return min(3, (floor - 1) // 3 + 1)


def _fortune(player):
    """Luck's cut of found credits: +2% per point."""
    return 1 + player.attributes.get("luck", 0) * 0.02


def _rng_for(seed, floor):
    return _random.Random(f"{seed}:{floor}")


def _key(x, y):
    return f"{x},{y}"


# --- Floor generation ---------------------------------------------------------


def generate_floor(seed, floor):
    """Deterministically generate a floor: a connected lattice graph of rooms
    with an entrance, a stairwell, puzzles, hidden rooms, and content."""
    rng = _rng_for(seed, floor)
    tier = _tier_for(floor)
    frags = data.load("dungeon_rooms")
    tier_frags = frags["tiers"][str(tier)]

    # 1) Layout: grow a connected set of positions from the entrance at (0,0).
    target = rng.randint(10, 13)
    positions = [(0, 0)]
    pos_set = {(0, 0)}
    edges = set()  # frozenset of two positions
    while len(positions) < target:
        base = rng.choice(positions)
        dx, dy = rng.choice(list(DIRS.values()))
        nxt = (base[0] + dx, base[1] + dy)
        if nxt in pos_set:
            continue
        positions.append(nxt)
        pos_set.add(nxt)
        edges.add(frozenset((base, nxt)))
    # A few extra corridors so floors have loops, not just branches.
    for a in positions:
        for dx, dy in DIRS.values():
            b = (a[0] + dx, a[1] + dy)
            if b in pos_set and frozenset((a, b)) not in edges and rng.random() < 0.15:
                edges.add(frozenset((a, b)))

    # 2) Rooms with flavor.
    names = list(tier_frags["names"])
    rng.shuffle(names)
    rooms = {}
    for i, (x, y) in enumerate(positions):
        rooms[_key(x, y)] = {
            "id": _key(x, y),
            "x": x,
            "y": y,
            "name": names[i % len(names)],
            "desc": rng.choice(tier_frags["descs"]),
            "exits": {},
            "content": {"type": "empty"},
            "visited": False,
        }
    for edge in edges:
        a, b = tuple(edge)
        for src, dst in ((a, b), (b, a)):
            direction = next(d for d, (dx, dy) in DIRS.items() if (src[0] + dx, src[1] + dy) == dst)
            rooms[_key(*src)]["exits"][direction] = {
                "to": _key(*dst),
                "label": rng.choice(frags["exit_labels"]),
                "hidden": False,
                "revealed": True,
            }

    # 3) Special rooms: entrance and the farthest room becomes the stairwell.
    entrance = _key(0, 0)
    rooms[entrance]["content"] = {"type": "stairs_up"}
    by_distance = _bfs_order(rooms, entrance)
    stairwell = by_distance[-1]
    boss_floor = floor in BOSS_BY_FLOOR
    rooms[stairwell]["content"] = {
        "type": "stairs_down",
        "locked": not boss_floor,  # puzzle floors lock the stairs
        "guard": BOSS_BY_FLOOR.get(floor),
        "guard_cleared": False,
    }

    # 4) Puzzle (non-boss floors) + miniboss hoard.
    fillable = [k for k in by_distance if rooms[k]["content"]["type"] == "empty" and k != entrance]
    puzzle = None
    if not boss_floor:
        puzzle = rng.choice(["keycard", "power"])
        if puzzle == "keycard":
            spot = rng.choice(fillable[len(fillable) // 3 :])  # not right by the door
            rooms[spot]["content"] = {"type": "keycard", "taken": False}
            fillable.remove(spot)
        else:
            spots = rng.sample(fillable, 2)
            for spot in spots:
                rooms[spot]["content"] = {"type": "generator", "on": False}
                fillable.remove(spot)
        # Optional miniboss hoard on puzzle floors.
        hoard = rng.choice(fillable[len(fillable) // 2 :])
        rooms[hoard]["content"] = {
            "type": "miniboss",
            "enemy": MINIBOSSES[(floor - 1) % len(MINIBOSSES)],
            "cleared": False,
        }
        fillable.remove(hoard)

    # 5) Hidden room(s) with premium caches, off a concealed exit.
    hidden_count = rng.randint(1, 2)
    for _ in range(hidden_count):
        host_key = rng.choice([k for k in fillable if k != stairwell] or fillable)
        host = rooms[host_key]
        free = [
            d
            for d, (dx, dy) in DIRS.items()
            if d not in host["exits"] and (host["x"] + dx, host["y"] + dy) not in pos_set
        ]
        if not free:
            continue
        d = rng.choice(free)
        dx, dy = DIRS[d]
        hx, hy = host["x"] + dx, host["y"] + dy
        hkey = _key(hx, hy)
        pos_set.add((hx, hy))
        rooms[hkey] = {
            "id": hkey,
            "x": hx,
            "y": hy,
            "name": "Sealed Cache",
            "desc": "A room the floor plans forgot on purpose. Someone hid good things here.",
            "exits": {
                OPPOSITE[d]: {
                    "to": host_key,
                    "label": "back through the concealed seam",
                    "hidden": False,
                    "revealed": True,
                }
            },
            "content": {"type": "cache", "looted": False},
            "visited": False,
        }
        host["exits"][d] = {
            "to": hkey,
            "label": "through the concealed seam",
            "hidden": True,
            "revealed": False,
        }
        host["hidden_hint"] = rng.choice(frags["hidden_hints"])

    # 6) Fill the rest: battles, events, treasure, rest.
    pool = [
        eid
        for eid, e in data.load("enemies").items()
        if e["role"] == "normal" and e["tier"] == tier
    ]
    events = list(data.load("dungeon_events"))
    for k in fillable:
        roll = rng.random()
        if roll < 0.45:
            rooms[k]["content"] = {"type": "battle", "enemy": rng.choice(pool), "cleared": False}
        elif roll < 0.62:
            rooms[k]["content"] = {"type": "event", "event": rng.choice(events), "done": False}
        elif roll < 0.80:
            rooms[k]["content"] = {"type": "treasure", "looted": False}
        elif roll < 0.90:
            rooms[k]["content"] = {"type": "rest", "used": False}
        # else stays empty — a quiet room with only its description.

    # 7) Curios: strange interactable objects scattered through the floor.
    curio_ids = list(data.load("curios"))
    rng.shuffle(curio_ids)
    hosts = [
        k
        for k, r in rooms.items()
        if r["content"]["type"] not in ("stairs_down", "cache") and k != entrance
    ]
    rng.shuffle(hosts)
    for host_key, curio_id in zip(hosts, curio_ids[: rng.randint(2, 3)]):
        rooms[host_key].setdefault("curios", []).append({"id": curio_id, "used": []})

    return {"rooms": rooms, "entrance": entrance, "stairwell": stairwell, "puzzle": puzzle}


def _bfs_order(rooms, start):
    seen = [start]
    queue = [start]
    while queue:
        cur = queue.pop(0)
        for exit_ in rooms[cur]["exits"].values():
            if exit_["to"] not in seen:
                seen.append(exit_["to"])
                queue.append(exit_["to"])
    return seen


# --- Run lifecycle --------------------------------------------------------------


def enter(player, clock, seed=None):
    if player.dungeon.get("active"):
        raise GameError("You're already inside the Substrate.")
    if player.location != ENTRANCE_DISTRICT:
        raise GameError("The way down is in The Shallows.")
    if player.energy < ENTER_ENERGY_COST:
        raise GameError("Too tired to brave the Substrate — rest first.")

    player.energy -= ENTER_ENERGY_COST
    clock.advance(ENTER_MINUTES)
    seed = seed if seed is not None else _random.randrange(1_000_000_000)
    floor_data = generate_floor(seed, 1)
    floor_data["rooms"][floor_data["entrance"]]["visited"] = True
    stats = combat.player_stats(player)
    player.dungeon = {
        "companion": _build_companion(player),
        "active": True,
        "seed": seed,
        "floor": 1,
        "rooms": floor_data["rooms"],
        "at": floor_data["entrance"],
        "prev": floor_data["entrance"],
        "stairwell": floor_data["stairwell"],
        "puzzle": floor_data["puzzle"],
        "keycard": False,
        "stairs_unlocked": floor_data["puzzle"] is None,
        "player_hp": stats["max_hp"],
        "attack_buff": 0,
        "pending_event": None,
        "cleared": False,
    }
    player.max_floor = max(player.max_floor, 1)
    return player.dungeon


def _require_run(player):
    if not player.dungeon.get("active"):
        raise GameError("You're not in the Substrate.")
    return player.dungeon


def _require_free(player):
    run = _require_run(player)
    if player.combat.get("active"):
        raise GameError("Something is in your way.")
    if run.get("pending_event"):
        raise GameError("Deal with what's in front of you first.")
    return run


# --- Actions ----------------------------------------------------------------------


def move(player, clock, direction, rng=None):
    """Step through an exit — a single action. Resolves the destination room."""
    rng = rng or _random
    run = _require_free(player)
    room = run["rooms"][run["at"]]
    exit_ = room["exits"].get(direction)
    if not exit_ or (exit_["hidden"] and not exit_["revealed"]):
        raise GameError("There's no way through there.")

    clock.advance(MOVE_MINUTES)
    run["prev"] = run["at"]
    run["at"] = exit_["to"]
    dest = run["rooms"][exit_["to"]]
    dest["visited"] = True
    return _resolve_room(player, run, dest, rng)


def _resolve_room(player, run, room, rng):
    content = room["content"]
    kind = content["type"]

    if kind in ("battle", "miniboss") and not content.get("cleared"):
        player.combat = combat.start(
            player,
            content["enemy"],
            run["floor"],
            run["player_hp"],
            run["attack_buff"],
            companion=run.get("companion"),
        )
        return {"type": kind, "text": player.combat["log"][0]}

    if kind == "stairs_down":
        guard = content.get("guard")
        if guard and not content.get("guard_cleared"):
            player.combat = combat.start(
                player,
                guard,
                run["floor"],
                run["player_hp"],
                run["attack_buff"],
                companion=run.get("companion"),
            )
            return {"type": "boss", "text": player.combat["log"][0]}
        return {"type": "stairs", "text": _stairs_text(run, content)}

    if kind == "treasure" and not content.get("looted"):
        content["looted"] = True
        if rng.random() < 0.5:
            amount = round(rng.randint(8, 20) * run["floor"] * _fortune(player))
            player.credits += amount
            return {"type": "treasure", "text": f"A cache of hard currency: +{amount} cr."}
        pool = ["stim_tea", "protein_cube", "star_ration"]
        if run["floor"] >= 4:
            pool += ["charge_cell", "nano_patch"]
        item_id = rng.choice(pool)
        inventory.add_item(player, item_id, 1)
        return {
            "type": "treasure",
            "text": f"Supplies, still sealed: 1x {inventory.get_item(item_id)['name']}.",
        }

    if kind == "cache" and not content.get("looted"):
        content["looted"] = True
        item_id = rng.choice(PREMIUM_LOOT)
        amount = round(rng.randint(15, 30) * run["floor"] * _fortune(player))
        inventory.add_item(player, item_id, 1)
        player.credits += amount
        return {
            "type": "cache",
            "text": (
                f"The hidden cache holds {inventory.get_item(item_id)['name']} "
                f"and {amount} cr in unmarked chits."
            ),
        }

    if kind == "rest" and not content.get("used"):
        content["used"] = True
        max_hp = combat.player_stats(player)["max_hp"]
        heal = round(max_hp * REST_HEAL_FRACTION)
        run["player_hp"] = min(max_hp, run["player_hp"] + heal)
        text = f"A defensible corner and quiet machinery. +{heal} HP."
        comp = run.get("companion")
        if comp and (comp["down"] or comp["hp"] < comp["max_hp"]):
            comp["down"] = False
            comp["hp"] = max(comp["hp"], round(comp["max_hp"] * 0.5))
            text += f" {comp['name']} patches up beside you."
        return {"type": "rest", "text": text}

    if kind == "event" and not content.get("done"):
        content["done"] = True
        run["pending_event"] = content["event"]
        return {"type": "event", "event": data.load("dungeon_events")[content["event"]]}

    if kind == "keycard" and not content.get("taken"):
        content["taken"] = True
        run["keycard"] = True
        return {
            "type": "keycard",
            "text": "Among the wreckage: a keycard, still warm. Somewhere a lock is waiting.",
        }

    if kind == "generator":
        state = "humming, alive" if content.get("on") else "dark, waiting"
        return {"type": "generator", "text": f"A floor generator — {state}."}

    return {"type": "room", "text": None}


def _stairs_text(run, content):
    if content.get("guard") and not content.get("guard_cleared"):
        return "The way down is occupied."
    if run["stairs_unlocked"] or not content.get("locked"):
        return "The stairwell spirals down into the dark. It's open."
    if run["puzzle"] == "keycard":
        if run.get("keycard"):
            run["stairs_unlocked"] = True
            return "The lock drinks the keycard and the bulkhead sighs open."
        return "A heavy bulkhead seals the stairs. The lock wants a keycard."
    return "The stairwell is dead — no power. Somewhere on this floor, generators sleep."


def search(player, clock, rng=None):
    """Search the current room for concealed exits (one action, Wit check)."""
    rng = rng or _random
    run = _require_free(player)
    room = run["rooms"][run["at"]]
    clock.advance(SEARCH_MINUTES)

    hidden = [(d, e) for d, e in room["exits"].items() if e["hidden"] and not e["revealed"]]
    if not hidden:
        return {"found": False, "text": "You search carefully. Nothing but honest walls."}
    # Wit does the looking; luck trips over the seam anyway.
    roll = (
        player.attributes.get("wit", 0) + player.attributes.get("luck", 0) // 3 + rng.randint(1, 6)
    )
    if roll < SEARCH_DC:
        return {
            "found": False,
            "text": "Something about this room nags at you, but it keeps its secret.",
        }
    for direction, exit_ in hidden:
        exit_["revealed"] = True
    words = ", ".join(DIR_WORD[d] for d, _ in hidden)
    return {"found": True, "text": f"There! A concealed way opens to the {words}."}


def interact(player, clock, rng=None):
    """Context action for the current room: flip a generator, or descend."""
    rng = rng or _random
    run = _require_free(player)
    room = run["rooms"][run["at"]]
    content = room["content"]

    if content["type"] == "generator" and not content.get("on"):
        content["on"] = True
        others = [
            r
            for r in run["rooms"].values()
            if r["content"]["type"] == "generator" and not r["content"].get("on")
        ]
        if not others:
            run["stairs_unlocked"] = True
            return {
                "type": "generator",
                "text": "The generator roars awake — and somewhere far off, a bulkhead unseals.",
            }
        return {
            "type": "generator",
            "text": "The generator roars awake. Its twin still sleeps somewhere.",
        }

    if content["type"] == "stairs_down":
        if content.get("guard") and not content.get("guard_cleared"):
            raise GameError("The way down is occupied.")
        if content.get("locked") and not run["stairs_unlocked"]:
            # Entering with the keycard unlocks via _stairs_text; re-check here.
            if run["puzzle"] == "keycard" and run.get("keycard"):
                run["stairs_unlocked"] = True
            else:
                raise GameError("The stairs are sealed. This floor hasn't given up its trick yet.")
        return descend(player, clock)

    raise GameError("Nothing here answers to that.")


def descend(player, clock):
    run = _require_run(player)
    if run["floor"] >= MAX_FLOOR:
        run["cleared"] = True
        return {
            "type": "cleared",
            "text": "Below the ninth floor there is only the Substrate's heartbeat. For now.",
        }
    run["floor"] += 1
    floor_data = generate_floor(run["seed"], run["floor"])
    floor_data["rooms"][floor_data["entrance"]]["visited"] = True
    run["rooms"] = floor_data["rooms"]
    run["at"] = floor_data["entrance"]
    run["prev"] = floor_data["entrance"]
    run["stairwell"] = floor_data["stairwell"]
    run["puzzle"] = floor_data["puzzle"]
    run["keycard"] = False
    run["stairs_unlocked"] = floor_data["puzzle"] is None
    player.max_floor = max(player.max_floor, run["floor"])
    clock.advance(MOVE_MINUTES)
    return {
        "type": "descend",
        "floor": run["floor"],
        "text": f"You descend. Floor {run['floor']} exhales around you.",
    }


def choose_event(player, choice_index, rng=None):
    """Resolve the pending room event with the chosen option."""
    rng = rng or _random
    run = _require_run(player)
    event_id = run.get("pending_event")
    if not event_id:
        raise GameError("There's nothing to decide here.")
    event = data.load("dungeon_events")[event_id]
    if not isinstance(choice_index, int) or not (0 <= choice_index < len(event["choices"])):
        raise GameError("Invalid choice.")
    choice = event["choices"][choice_index]

    cost = choice.get("cost", 0)
    if cost:
        if player.credits < cost:
            raise GameError("Not enough credits.")
        player.credits -= cost

    if "stat" in choice:
        roll = player.attributes.get(choice["stat"], 0) + rng.randint(1, 6)
        outcome = choice["success"] if roll >= choice["dc"] else choice["failure"]
    else:
        outcome = choice["outcome"]

    run["pending_event"] = None
    return _apply_outcome(player, run, outcome)


def _apply_outcome(player, run, outcome):
    kind = outcome["type"]
    if kind == "credits":
        player.credits += outcome["amount"]
    elif kind == "heal":
        max_hp = combat.player_stats(player)["max_hp"]
        run["player_hp"] = min(max_hp, run["player_hp"] + outcome["amount"])
    elif kind == "damage":
        run["player_hp"] = max(1, run["player_hp"] - outcome["amount"])
    elif kind == "buff":
        run["attack_buff"] = run.get("attack_buff", 0) + outcome["amount"]
    elif kind == "item":
        inventory.add_item(player, outcome["item"], 1)
    elif kind == "xp":
        combat.grant_xp(player, outcome["amount"])
    elif kind == "xp_damage":
        combat.grant_xp(player, outcome["xp"])
        run["player_hp"] = max(1, run["player_hp"] - outcome["amount"])
    elif kind == "buff_damage":
        run["attack_buff"] = run.get("attack_buff", 0) + outcome["amount"]
        run["player_hp"] = max(1, run["player_hp"] - outcome["damage"])
    elif kind == "reveal":
        for room in run["rooms"].values():
            room["visited"] = True
    return {"type": kind, "text": outcome["text"]}


def finish_combat(player):
    """Fold a finished battle back into the run."""
    run = _require_run(player)
    state = player.combat
    if not state.get("over"):
        raise GameError("The fight isn't over.")

    room = run["rooms"][run["at"]]
    content = room["content"]

    if state["victory"]:
        run["player_hp"] = state["player_hp"]
        if state.get("companion"):
            run["companion"] = state["companion"]
        # Carry the rewards out of the (about-to-be-discarded) battle state so
        # the client can show a victory screen.
        result = {
            "result": "victory",
            "enemy": state["enemy"]["name"],
            "rewards": state.get("rewards"),
        }
        if content["type"] == "stairs_down":
            content["guard_cleared"] = True
        else:
            content["cleared"] = True
            if content["type"] == "miniboss":
                # The hoard: premium loot behind the optional miniboss.
                item_id = _random.choice(PREMIUM_LOOT)
                amount = round(_random.randint(20, 40) * run["floor"] * _fortune(player))
                inventory.add_item(player, item_id, 1)
                player.credits += amount
                result["hoard"] = (
                    f"The hoard is yours: {inventory.get_item(item_id)['name']} and {amount} cr."
                )
        player.combat = {}
        return result

    if state["fled"]:
        run["player_hp"] = state["player_hp"]
        if state.get("companion"):
            run["companion"] = state["companion"]
        run["at"] = run["prev"]  # you retreat the way you came
        player.combat = {}
        return {"result": "fled"}

    lost = round(player.credits * DEFEAT_CREDIT_LOSS)
    companion_id = (run.get("companion") or {}).get("id")
    player.credits -= lost
    player.combat = {}
    player.dungeon = {}
    return {
        "result": "defeat",
        "enemy": state["enemy"]["name"],
        "credits_lost": lost,
        "companion": companion_id,
    }


def leave(player, clock):
    run = _require_run(player)
    if player.combat.get("active"):
        raise GameError("Not with something blocking the way out.")
    clock.advance(ENTER_MINUTES)
    floor = run["floor"]
    companion_id = (run.get("companion") or {}).get("id")
    player.dungeon = {}
    return {"left_at_floor": floor, "companion": companion_id}


def _build_companion(player):
    """Materialise the recruited companion for a run (None = delving solo)."""
    if not player.companion:
        return None
    entry = data.load("characters").get(player.companion)
    if not entry or "companion" not in entry:
        return None
    spec = entry["companion"]
    level = player.combat_level
    max_hp = round((20 + level * 8) * spec["hp_mult"])
    return {
        "id": player.companion,
        "name": entry["name"],
        "role": spec["role"],
        "element": spec["element"],
        "blurb": spec.get("blurb", ""),
        "hp": max_hp,
        "max_hp": max_hp,
        "attack": round((5 + level * 1.8) * spec["atk_mult"]),
        "defense": 2 + level,
        "credit_bonus": spec.get("credit_bonus", 0),
        "down": False,
    }


def curio_act(player, clock, curio_id, verb, rng=None):
    """Interact with a curio in the current room. Examine is free; other verbs
    are one actions (5m) and usually one-shot."""
    rng = rng or _random
    run = _require_free(player)
    room = run["rooms"][run["at"]]
    entry = next((c for c in room.get("curios", []) if c["id"] == curio_id), None)
    if entry is None:
        raise GameError("There's nothing like that here.")
    curio = data.load("curios")[curio_id]

    if verb == "examine":
        return {"type": "examine", "text": curio["examine"]}

    spec = curio["verbs"].get(verb)
    if spec is None:
        raise GameError(f"You can't {verb} the {curio['name']}.")
    if spec.get("once") and verb in entry["used"]:
        raise GameError("It has given what it has to give.")

    clock.advance(MOVE_MINUTES)
    entry["used"].append(verb)
    outcome = _apply_outcome(player, run, spec["outcome"])
    return {"type": "curio", "text": spec["text"], "outcome": outcome}


# --- Fog-of-war view --------------------------------------------------------------


def view(player):
    """What the player knows: visited rooms in full, revealed-exit stubs, and
    the current room's detail (exits, hints, contextual action)."""
    run = _require_run(player)
    rooms = run["rooms"]
    here = rooms[run["at"]]

    map_rooms = []
    stubs = set()
    for room in rooms.values():
        if room["visited"]:
            map_rooms.append(
                {
                    "id": room["id"],
                    "x": room["x"],
                    "y": room["y"],
                    "name": room["name"],
                    "type": room["content"]["type"],
                    "resolved": _is_resolved(room["content"]),
                    "current": room["id"] == run["at"],
                }
            )
            for exit_ in room["exits"].values():
                if (exit_["revealed"] or not exit_["hidden"]) and not rooms[exit_["to"]]["visited"]:
                    stubs.add(exit_["to"])
    for stub_id in stubs:
        stub = rooms[stub_id]
        map_rooms.append({"id": stub_id, "x": stub["x"], "y": stub["y"], "stub": True})

    frags = data.load("dungeon_rooms")
    exits = []
    hints = []
    if here.get("hidden_hint") and any(
        e["hidden"] and not e["revealed"] for e in here["exits"].values()
    ):
        hints.append(here["hidden_hint"])
    for direction in ("n", "e", "s", "w"):
        exit_ = here["exits"].get(direction)
        if not exit_ or (exit_["hidden"] and not exit_["revealed"]):
            continue
        dest = rooms[exit_["to"]]
        threat = dest["content"]["type"] in ("battle", "miniboss") and not dest["content"].get(
            "cleared"
        )
        if (
            dest["content"]["type"] == "stairs_down"
            and dest["content"].get("guard")
            and not dest["content"].get("guard_cleared")
        ):
            threat = True
        if threat and not dest["visited"]:
            hints.append(
                _rng_for(run["seed"], f"hint:{here['id']}:{direction}")
                .choice(frags["battle_hints"])
                .replace("{dir}", DIR_WORD[direction])
            )
        exits.append(
            {
                "dir": direction,
                "word": DIR_WORD[direction],
                "label": exit_["label"],
                "known": dest["visited"],
            }
        )

    content = here["content"]
    interact_label = None
    if content["type"] == "generator" and not content.get("on"):
        interact_label = "Start the generator"
    elif content["type"] == "stairs_down":
        if not (content.get("guard") and not content.get("guard_cleared")):
            interact_label = "Descend the stairs"

    curios = []
    for entry in here.get("curios", []):
        curio = data.load("curios")[entry["id"]]
        verbs = [v for v in curio["verbs"] if v not in entry["used"]]
        curios.append(
            {"id": entry["id"], "name": curio["name"], "short": curio["short"], "verbs": verbs}
        )

    return {
        "floor": run["floor"],
        "map": map_rooms,
        "companion": run.get("companion"),
        "here": {
            "id": here["id"],
            "name": here["name"],
            "desc": here["desc"],
            "type": content["type"],
            "exits": exits,
            "hints": hints,
            "curios": curios,
            "interact": interact_label,
            "stairs_note": _stairs_note(run, content),
        },
        "player_hp": run["player_hp"],
        "cleared": run.get("cleared", False),
        "pending_event": run.get("pending_event"),
    }


def _stairs_note(run, content):
    if content["type"] != "stairs_down":
        return None
    if content.get("guard") and not content.get("guard_cleared"):
        return "The way down is occupied."
    if run["stairs_unlocked"]:
        return "The stairwell is open."
    if run["puzzle"] == "keycard":
        return (
            "Sealed — the lock wants a keycard." if not run.get("keycard") else "The keycard fits."
        )
    return "Dead — the floor's generators are offline."


def _is_resolved(content):
    kind = content["type"]
    if kind in ("battle", "miniboss"):
        return bool(content.get("cleared"))
    if kind in ("treasure", "cache"):
        return bool(content.get("looted"))
    if kind == "rest":
        return bool(content.get("used"))
    if kind == "event":
        return bool(content.get("done"))
    if kind == "keycard":
        return bool(content.get("taken"))
    if kind == "generator":
        return bool(content.get("on"))
    if kind == "stairs_down":
        return bool(content.get("guard_cleared")) or not content.get("guard")
    return True
