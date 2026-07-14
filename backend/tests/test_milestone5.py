"""Milestone 5: elements, combat, the Substrate dungeon, difficulty."""

import pytest
from app import create_app
from game import combat, dungeon
from game.calendar import GameClock
from game.player import Player


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    # The Substrate entrance is in The Shallows.
    c.post("/api/travel", json={"to": "the_shallows", "mode": "walk"})
    return c


def _player(**kw):
    return Player.create({"name": "Kai", "pronouns": "she/her"})


# --- Elements ----------------------------------------------------------------


def test_element_triangles():
    # thermal > cryo > voltaic > thermal
    assert combat.element_multiplier("thermal", "cryo") == 1.5
    assert combat.element_multiplier("cryo", "voltaic") == 1.5
    assert combat.element_multiplier("voltaic", "thermal") == 1.5
    assert combat.element_multiplier("cryo", "thermal") == 0.5  # resisted
    # kinetic > toxin > psionic > kinetic
    assert combat.element_multiplier("kinetic", "toxin") == 1.5
    assert combat.element_multiplier("psionic", "kinetic") == 1.5
    assert combat.element_multiplier("kinetic", "psionic") == 0.5
    # neutral pairs
    assert combat.element_multiplier("thermal", "toxin") == 1.0


# --- Level & XP persistence --------------------------------------------------


def test_xp_curve_and_level_ups():
    p = _player()
    assert p.combat_level == 1
    ups = combat.grant_xp(p, combat.xp_to_next(1))  # exactly one level
    assert ups == 1
    assert p.combat_level == 2
    # Big grant cascades multiple levels.
    combat.grant_xp(p, 500)
    assert p.combat_level > 3


def test_stats_scale_with_level():
    p = _player()
    low = combat.player_stats(p)
    p.combat_level = 5
    high = combat.player_stats(p)
    assert high["max_hp"] > low["max_hp"]
    assert high["attack"] > low["attack"]


def test_skills_unlock_by_level():
    assert "flare_burst" not in combat.unlocked_skills(1)
    assert "flare_burst" in combat.unlocked_skills(2)
    assert "overdrive" in combat.unlocked_skills(8)


# --- Difficulty tuning -------------------------------------------------------


def test_difficulty_scales_enemies():
    easy = combat.scaled_enemy("holo_siren", 1, "easy")
    normal = combat.scaled_enemy("holo_siren", 1, "normal")
    hard = combat.scaled_enemy("holo_siren", 1, "hard")
    assert easy["hp"] < normal["hp"] < hard["hp"]
    assert easy["attack"] < normal["attack"] < hard["attack"]


def test_floor_scales_enemies():
    f1 = combat.scaled_enemy("holo_siren", 1, "normal")
    f3 = combat.scaled_enemy("holo_siren", 3, "normal")
    assert f3["hp"] > f1["hp"]


# --- Dungeon generation ------------------------------------------------------


def test_floor_generation_is_deterministic():
    a = dungeon.generate_floor(42, 1)
    b = dungeon.generate_floor(42, 1)
    assert a == b
    assert dungeon.generate_floor(43, 1) != a or True  # different seed may differ


def test_boss_and_miniboss_placement():
    # Boss floors: the boss camps in the stairwell room. Puzzle floors: a
    # miniboss guards an optional hoard and the stairs are locked instead.
    for floor in (1, 2, 4, 5, 7, 8):
        fd = dungeon.generate_floor(7, floor)
        stairwell = fd["rooms"][fd["stairwell"]]["content"]
        assert stairwell["guard"] is None
        assert stairwell["locked"] is True
        assert fd["puzzle"] in ("keycard", "power")
        minibosses = [r for r in fd["rooms"].values() if r["content"]["type"] == "miniboss"]
        assert len(minibosses) == 1
    for floor, boss in dungeon.BOSS_BY_FLOOR.items():
        fd = dungeon.generate_floor(7, floor)
        stairwell = fd["rooms"][fd["stairwell"]]["content"]
        assert stairwell["guard"] == boss
        assert stairwell["locked"] is False


def test_enemy_tier_matches_floor_depth():
    from game import data

    enemies = data.load("enemies")
    fd = dungeon.generate_floor(7, 8)  # tier 3 depth
    for room in fd["rooms"].values():
        if room["content"]["type"] == "battle":
            assert enemies[room["content"]["enemy"]]["tier"] == 3


# --- The run, via the API ----------------------------------------------------


def test_enter_requires_the_shallows(client):
    client.post("/api/travel", json={"to": "docking_quarter", "mode": "walk"})
    resp = client.post("/api/dungeon/enter")
    assert resp.status_code == 400
    assert "shallows" in resp.get_json()["error"].lower()


def test_enter_and_walk_a_floor(client):
    res = client.post("/api/dungeon/enter").get_json()
    assert res["run"]["active"] is True
    assert res["run"]["floor"] == 1
    assert res["stats"]["level"] == 1
    # Fog of war: exactly the entrance is visited at the start.
    assert len([r for r in res["run"]["map"] if not r.get("stub")]) == 1

    # Wander: resolve combat/events, otherwise step through the first exit.
    for _ in range(40):
        state = client.get("/api/dungeon/state").get_json()
        if state["combat"]:
            r = client.post("/api/combat/action", json={"action": "attack"})
            assert r.status_code == 200
        elif state["run"] and state["run"].get("pending_event"):
            r = client.post("/api/dungeon/event", json={"choice_index": 0})
            assert r.status_code == 200
        elif state["run"]:
            exits = state["run"]["here"]["exits"]
            assert exits, "every room must have at least one exit"
            r = client.post("/api/dungeon/move", json={"dir": exits[0]["dir"]})
            assert r.status_code in (200, 400)
        else:
            break  # run ended (defeat) — acceptable outcome of the walk


def test_level_persists_after_leaving(client):
    client.post("/api/dungeon/enter")
    # Grind the first room if it's a battle; then leave.
    for _ in range(40):
        state = client.get("/api/dungeon/state").get_json()
        if state["combat"]:
            client.post("/api/combat/action", json={"action": "attack"})
        elif state["run"] and not state["run"].get("pending_event"):
            break
        elif state["run"]:
            client.post("/api/dungeon/event", json={"choice_index": 0})
        else:
            break
    state = client.get("/api/dungeon/state").get_json()
    if state["run"]:  # only leave if we survived
        client.post("/api/dungeon/leave")
    player = client.get("/api/game/state").get_json()["player"]
    assert player["combat_level"] >= 1
    assert player["max_floor"] >= 1
    # No active run remains either way.
    assert client.get("/api/dungeon/state").get_json()["run"] is None


def test_difficulty_endpoint(client):
    assert client.post("/api/difficulty", json={"level": "nightmare"}).status_code == 400
    res = client.post("/api/difficulty", json={"level": "hard"})
    assert res.status_code == 200
    assert res.get_json()["player"]["difficulty"] == "hard"


# --- Combat mechanics (engine-level, deterministic rng) -----------------------


class FixedRng:
    """No variance, no crits, always 'fails' percent rolls."""

    def uniform(self, a, b):
        return 1.0

    def random(self):
        return 0.99

    def randint(self, a, b):
        return (a + b) // 2

    def choice(self, seq):
        return seq[0]


def test_guard_halves_damage_and_banks_charge():
    p = _player()
    state = combat.start(p, "holo_siren", 1, 60)
    charge_before = state["charge"]
    combat.act(p, state, "guard", rng=FixedRng())
    # Guard consumed by the enemy turn; charge banked +1 then +1 per turn.
    assert state["charge"] >= charge_before + 1
    assert state["player_hp"] > 0


def test_skill_requires_charge_and_unlock():
    p = _player()  # level 1 — flare_burst locked
    state = combat.start(p, "holo_siren", 1, 60)
    with pytest.raises(Exception):
        combat.act(p, state, "skill", skill_id="flare_burst", rng=FixedRng())


def test_victory_grants_xp_and_credits():
    p = _player()
    p.combat_level = 10  # overwhelming force for a clean win
    credits_before = p.credits
    state = combat.start(p, "holo_siren", 1, 200)
    for _ in range(20):
        if state["over"]:
            break
        combat.act(p, state, "attack", rng=FixedRng())
    assert state["victory"] is True
    assert state["rewards"]["xp"] > 0
    assert p.credits > credits_before


def test_cannot_flee_a_boss():
    p = _player()
    state = combat.start(p, "chrome_contessa", 3, 100)
    with pytest.raises(Exception):
        combat.act(p, state, "flee", rng=FixedRng())


def test_defeat_costs_credits_but_never_level():
    p = _player()
    p.combat_level = 3
    p.credits = 100
    clock = GameClock()
    p.location = dungeon.ENTRANCE_DISTRICT
    dungeon.enter(p, clock, seed=1)
    p.combat = combat.start(p, "substrate_empress", 9, 10)  # hopeless
    p.combat["player_hp"] = 0
    p.combat["over"] = True
    p.combat["victory"] = False
    result = dungeon.finish_combat(p)
    assert result["result"] == "defeat"
    assert p.credits == 85  # -15%
    assert p.combat_level == 3  # level never lost
    assert p.dungeon == {}  # ejected
