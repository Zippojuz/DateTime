"""The Zork-style Substrate: graph floors, fog of war, hidden rooms, puzzles."""

import pytest
from game import dungeon
from game.calendar import GameClock
from game.player import Player


def _delver(wit=5, level=8):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.combat_level = level
    p.attributes["wit"] = wit
    p.location = dungeon.ENTRANCE_DISTRICT
    return p


def _enter(p, seed=7):
    clock = GameClock()
    dungeon.enter(p, clock, seed=seed)
    return clock


class HighRoll:
    def randint(self, a, b):
        return b

    def random(self):
        return 0.99

    def choice(self, seq):
        return seq[0]


class LowRoll(HighRoll):
    def randint(self, a, b):
        return a


# --- Generation ---------------------------------------------------------------


def test_floor_is_connected_and_exits_are_mutual():
    fd = dungeon.generate_floor(42, 1)
    rooms = fd["rooms"]
    # Connected: BFS from the entrance reaches every room (via all exits).
    reached = {fd["entrance"]}
    queue = [fd["entrance"]]
    while queue:
        cur = queue.pop(0)
        for e in rooms[cur]["exits"].values():
            if e["to"] not in reached:
                reached.add(e["to"])
                queue.append(e["to"])
    assert reached == set(rooms)
    # Mutual: every exit has a matching reverse exit.
    for room in rooms.values():
        for d, e in room["exits"].items():
            back = rooms[e["to"]]["exits"][dungeon.OPPOSITE[d]]
            assert back["to"] == room["id"]


def test_generation_is_deterministic():
    assert dungeon.generate_floor(99, 4) == dungeon.generate_floor(99, 4)


def test_every_floor_has_a_hidden_cache():
    for floor in range(1, 10):
        fd = dungeon.generate_floor(11, floor)
        caches = [r for r in fd["rooms"].values() if r["content"]["type"] == "cache"]
        assert 1 <= len(caches) <= 2
        # Each cache is behind an exit that starts concealed.
        for cache in caches:
            hosts = [
                r
                for r in fd["rooms"].values()
                for d, e in r["exits"].items()
                if e["to"] == cache["id"] and e["hidden"]
            ]
            assert hosts, "cache must be behind a hidden exit"


# --- Movement & fog of war ------------------------------------------------------


def test_move_is_one_action_and_reveals_the_map():
    p = _delver()
    clock = _enter(p)
    view = dungeon.view(p)
    start_minutes = clock.minute_of_day
    exits = view["here"]["exits"]
    assert exits
    dungeon.move(p, clock, exits[0]["dir"], rng=HighRoll())
    assert clock.minute_of_day - start_minutes == dungeon.MOVE_MINUTES
    after = dungeon.view(p)
    visited = [r for r in after["map"] if not r.get("stub")]
    assert len(visited) == 2  # entrance + the new room


def test_cannot_walk_through_walls():
    p = _delver()
    clock = _enter(p)
    view = dungeon.view(p)
    open_dirs = {e["dir"] for e in view["here"]["exits"]}
    blocked = next(d for d in "nsew" if d not in open_dirs) if open_dirs != set("nsew") else None
    if blocked:
        with pytest.raises(Exception):
            dungeon.move(p, clock, blocked)


def test_fog_of_war_hides_unvisited_room_details():
    p = _delver()
    _enter(p)
    view = dungeon.view(p)
    for room in view["map"]:
        if room.get("stub"):
            assert "name" not in room  # stubs expose position only
            assert "type" not in room


# --- Hidden rooms & search -------------------------------------------------------


def _find_hidden_host(p):
    run = p.dungeon
    for room in run["rooms"].values():
        for e in room["exits"].values():
            if e["hidden"] and not e["revealed"]:
                return room["id"]
    return None


def test_search_reveals_concealed_exit_with_wit():
    p = _delver(wit=10)
    clock = _enter(p)
    host = _find_hidden_host(p)
    assert host is not None
    p.dungeon["at"] = host  # teleport for the test
    result = dungeon.search(p, clock, rng=HighRoll())
    assert result["found"] is True
    # The exit is now traversable and leads to a premium cache.
    hidden_dir = next(
        d for d, e in p.dungeon["rooms"][host]["exits"].items() if e["revealed"] and e["hidden"]
    )
    res = dungeon.move(p, clock, hidden_dir, rng=HighRoll())
    assert res["type"] == "cache"
    assert p.credits > 50  # cache pays out


def test_search_can_fail_on_low_wit():
    p = _delver(wit=0)
    clock = _enter(p)
    host = _find_hidden_host(p)
    p.dungeon["at"] = host
    result = dungeon.search(p, clock, rng=LowRoll())
    assert result["found"] is False


def test_search_hint_appears_in_room_view():
    p = _delver()
    _enter(p)
    host = _find_hidden_host(p)
    p.dungeon["at"] = host
    p.dungeon["rooms"][host]["visited"] = True
    view = dungeon.view(p)
    assert view["here"]["hints"], "rooms with concealed exits should hint at them"


# --- Puzzles ---------------------------------------------------------------------


def _floor_with_puzzle(kind, start_seed=1):
    seed = start_seed
    while True:
        fd = dungeon.generate_floor(seed, 1)
        if fd["puzzle"] == kind:
            return seed, fd
        seed += 1


def test_keycard_unlocks_the_stairs():
    seed, fd = _floor_with_puzzle("keycard")
    p = _delver()
    clock = _enter(p, seed=seed)
    run = p.dungeon
    # Stairs sealed before the keycard.
    run["at"] = run["stairwell"]
    with pytest.raises(Exception):
        dungeon.interact(p, clock)
    # Grab the keycard.
    card_room = next(k for k, r in run["rooms"].items() if r["content"]["type"] == "keycard")
    run["at"] = card_room
    res = dungeon._resolve_room(p, run, run["rooms"][card_room], HighRoll())
    assert res["type"] == "keycard"
    assert run["keycard"] is True
    # Now the stairwell opens and descends.
    run["at"] = run["stairwell"]
    res = dungeon.interact(p, clock)
    assert res["type"] == "descend"
    assert run["floor"] == 2


def test_power_routing_unlocks_the_stairs():
    seed, fd = _floor_with_puzzle("power")
    p = _delver()
    clock = _enter(p, seed=seed)
    run = p.dungeon
    generators = [k for k, r in run["rooms"].items() if r["content"]["type"] == "generator"]
    assert len(generators) == 2
    run["at"] = generators[0]
    res = dungeon.interact(p, clock)
    assert "twin still sleeps" in res["text"]
    assert run["stairs_unlocked"] is False
    run["at"] = generators[1]
    res = dungeon.interact(p, clock)
    assert run["stairs_unlocked"] is True
    run["at"] = run["stairwell"]
    assert dungeon.interact(p, clock)["type"] == "descend"


def test_boss_floor_stairs_need_the_boss_dead():
    p = _delver(level=12)
    clock = _enter(p, seed=5)
    run = p.dungeon
    run["floor"] = 3  # simulate being on a boss floor
    fd = dungeon.generate_floor(run["seed"], 3)
    run["rooms"], run["stairwell"], run["puzzle"] = fd["rooms"], fd["stairwell"], fd["puzzle"]
    run["stairs_unlocked"] = True
    run["at"] = run["stairwell"]
    # Entering the stairwell starts the boss fight.
    res = dungeon._resolve_room(p, run, run["rooms"][run["stairwell"]], HighRoll())
    assert res["type"] == "boss"
    assert p.combat["enemy"]["id"] == "chrome_contessa"
    # Can't descend past her.
    p.combat = {}
    with pytest.raises(Exception):
        dungeon.interact(p, clock)
    # Once she falls, the way opens.
    run["rooms"][run["stairwell"]]["content"]["guard_cleared"] = True
    assert dungeon.interact(p, clock)["type"] == "descend"


# --- Telegraphs & flee --------------------------------------------------------


def test_uncleared_threats_leak_hints_through_doors():
    p = _delver()
    _enter(p)
    run = p.dungeon
    # Find a room adjacent to an uncleared battle and stand in it.
    for room in run["rooms"].values():
        for e in room["exits"].values():
            dest = run["rooms"][e["to"]]
            if dest["content"]["type"] in ("battle", "miniboss") and not e["hidden"]:
                run["at"] = room["id"]
                room["visited"] = True
                view = dungeon.view(p)
                assert any(
                    w in " ".join(view["here"]["hints"])
                    for w in ("ticking", "scrape", "glimmer", "song")
                )
                return
    pytest.skip("seed produced no adjacent battle")


def test_fleeing_returns_you_to_the_previous_room():
    p = _delver()
    _enter(p)
    run = p.dungeon
    # Walk into a battle room.
    battle_key = next(k for k, r in run["rooms"].items() if r["content"]["type"] == "battle")
    start = run["at"]
    run["rooms"][battle_key]["visited"] = True
    run["prev"] = start
    run["at"] = battle_key
    from game import combat as combat_mod

    p.combat = combat_mod.start(p, run["rooms"][battle_key]["content"]["enemy"], 1, 100)
    p.combat["over"] = True
    p.combat["fled"] = True
    p.combat["victory"] = False
    result = dungeon.finish_combat(p)
    assert result["result"] == "fled"
    assert run["at"] == start  # back the way you came
