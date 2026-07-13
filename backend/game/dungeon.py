"""The Substrate — a procedurally generated dungeon beneath Nexus City. (M5)

Floors are generated from a per-run seed, so a run resumes deterministically
after a reload. Each floor is a short chain of rooms (battles, events, treasure,
rest) capped by a miniboss — or a main boss every third floor. Nine floors for
now; combat level and max-floor progress persist on the player across runs.

Entered from The Shallows ("lower city, danger" — and the first thread of the
city's dark secret).
"""

import random as _random

from game import combat, data, inventory
from game.errors import GameError

ENTRANCE_DISTRICT = "the_shallows"
MAX_FLOOR = 9
ROOMS_PER_FLOOR = 6
ENTER_ENERGY_COST = 10
ENTER_MINUTES = 30
ROOM_MINUTES = 10
DEFEAT_CREDIT_LOSS = 0.15  # lose 15% of credits when you go down
REST_HEAL_FRACTION = 0.4

# Weighted room types for the non-final rooms of a floor.
_ROOM_POOL = ["battle", "battle", "battle", "event", "treasure", "rest"]

BOSS_BY_FLOOR = {3: "chrome_contessa", 6: "neon_seraph", 9: "substrate_empress"}
MINIBOSSES = ["warden_lyss", "overclock_queen", "spore_matriarch"]


def _tier_for(floor):
    return min(3, (floor - 1) // 3 + 1)


def _rng_for(seed, floor):
    return _random.Random(f"{seed}:{floor}")


def generate_floor(seed, floor):
    """Deterministically generate a floor's room list from the run seed."""
    rng = _rng_for(seed, floor)
    tier = _tier_for(floor)
    pool = [
        eid
        for eid, e in data.load("enemies").items()
        if e["role"] == "normal" and e["tier"] == tier
    ]
    events = list(data.load("dungeon_events"))

    rooms = []
    for _ in range(ROOMS_PER_FLOOR - 1):
        kind = rng.choice(_ROOM_POOL)
        room = {"type": kind, "done": False}
        if kind == "battle":
            room["enemy"] = rng.choice(pool)
        elif kind == "event":
            room["event"] = rng.choice(events)
        rooms.append(room)

    if floor in BOSS_BY_FLOOR:
        rooms.append({"type": "boss", "enemy": BOSS_BY_FLOOR[floor], "done": False})
    else:
        miniboss = MINIBOSSES[(floor - 1) % len(MINIBOSSES)]
        rooms.append({"type": "miniboss", "enemy": miniboss, "done": False})
    return rooms


def enter(player, clock, seed=None):
    """Start (or refuse) a dungeon run. Mutates player/clock in place."""
    if player.dungeon.get("active"):
        raise GameError("You're already inside the Substrate.")
    if player.location != ENTRANCE_DISTRICT:
        raise GameError("The way down is in The Shallows.")
    if player.energy < ENTER_ENERGY_COST:
        raise GameError("Too tired to brave the Substrate — rest first.")

    player.energy -= ENTER_ENERGY_COST
    clock.advance(ENTER_MINUTES)
    seed = seed if seed is not None else _random.randrange(1_000_000_000)
    stats = combat.player_stats(player)
    player.dungeon = {
        "active": True,
        "seed": seed,
        "floor": 1,
        "room": -1,  # advances to 0 on the first step
        "rooms": generate_floor(seed, 1),
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


def advance(player, clock, rng=None):
    """Step to the next room and resolve what's there. Returns a result dict;
    battles land in player.combat, events in dungeon['pending_event']."""
    rng = rng or _random
    run = _require_run(player)
    if player.combat.get("active"):
        raise GameError("Something is still in your way.")
    if run.get("pending_event"):
        raise GameError("Deal with what's in front of you first.")

    # Past the last room -> descend to the next floor (or finish the run).
    if run["room"] >= len(run["rooms"]) - 1:
        if run["floor"] >= MAX_FLOOR:
            run["cleared"] = True
            return {
                "type": "cleared",
                "text": "The Substrate has no deeper floor to give you. For now.",
            }
        run["floor"] += 1
        run["room"] = -1
        run["rooms"] = generate_floor(run["seed"], run["floor"])
        player.max_floor = max(player.max_floor, run["floor"])
        clock.advance(ROOM_MINUTES)
        return {
            "type": "descend",
            "floor": run["floor"],
            "text": f"You descend. Floor {run['floor']} hums awake around you.",
        }

    run["room"] += 1
    room = run["rooms"][run["room"]]
    clock.advance(ROOM_MINUTES)

    if room["type"] in ("battle", "miniboss", "boss"):
        player.combat = combat.start(
            player, room["enemy"], run["floor"], run["player_hp"], run["attack_buff"]
        )
        return {"type": room["type"], "text": player.combat["log"][0]}

    if room["type"] == "treasure":
        room["done"] = True
        if rng.random() < 0.5:
            amount = rng.randint(8, 20) * run["floor"]
            player.credits += amount
            return {"type": "treasure", "text": f"A cache of hard currency: +{amount} cr."}
        item_id = rng.choice(["stim_tea", "protein_cube", "star_ration"])
        inventory.add_item(player, item_id, 1)
        name = inventory.get_item(item_id)["name"]
        return {"type": "treasure", "text": f"Supplies, still sealed: 1x {name}."}

    if room["type"] == "rest":
        room["done"] = True
        max_hp = combat.player_stats(player)["max_hp"]
        heal = round(max_hp * REST_HEAL_FRACTION)
        run["player_hp"] = min(max_hp, run["player_hp"] + heal)
        return {"type": "rest", "text": f"A defensible corner and quiet machinery. +{heal} HP."}

    # Event room: park it as pending until the player chooses.
    event = data.load("dungeon_events")[room["event"]]
    run["pending_event"] = room["event"]
    room["done"] = True
    return {"type": "event", "event": event}


def choose_event(player, choice_index, rng=None):
    """Resolve the pending event with the chosen option. Returns outcome dict."""
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

    if "stat" in choice:  # a stat check: attribute + d6 vs dc
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
    return {"type": kind, "text": outcome["text"]}


def finish_combat(player):
    """Fold a finished battle back into the run. Returns a status dict."""
    run = _require_run(player)
    state = player.combat
    if not state.get("over"):
        raise GameError("The fight isn't over.")

    if state["victory"]:
        run["player_hp"] = state["player_hp"]
        run["rooms"][run["room"]]["done"] = True
        player.combat = {}
        return {"result": "victory"}

    if state["fled"]:
        run["player_hp"] = state["player_hp"]
        # Fleeing does NOT clear the room; advancing will be blocked by it...
        # so step back one room: you retreat the way you came.
        run["room"] = max(-1, run["room"] - 1)
        player.combat = {}
        return {"result": "fled"}

    # Defeat: ejected from the Substrate. Level/XP are kept ("remember your
    # level"); the toll is credits.
    lost = round(player.credits * DEFEAT_CREDIT_LOSS)
    player.credits -= lost
    player.combat = {}
    player.dungeon = {}
    return {"result": "defeat", "credits_lost": lost}


def leave(player, clock):
    """Walk out between fights. Progress (level, max floor) persists."""
    run = _require_run(player)
    if player.combat.get("active"):
        raise GameError("Not with something blocking the way out.")
    clock.advance(ENTER_MINUTES)
    player.dungeon = {}
    return {"left_at_floor": run["floor"]}
