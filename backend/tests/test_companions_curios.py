"""Companions (one-at-a-time party) and curios (Zork-style room objects)."""

import pytest
from app import create_app
from game import combat, dungeon, inventory, save, social
from game.calendar import GameClock
from game.player import Player


class QuietRng:
    """No crits/variance; never passes chance rolls; picks first choice."""

    def uniform(self, a, b):
        return 1.0

    def random(self):
        return 0.99

    def choice(self, seq):
        return seq[0]

    def randint(self, a, b):
        return b


class TankTargetRng(QuietRng):
    """random()=0.5: targets a tank (0.55) but not other roles (0.25);
    no crits (0.10), no enemy skills (0.30)."""

    def random(self):
        return 0.5


def _player(level=5):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.combat_level = level
    return p


def _ally(role, element="cryo", credit_bonus=0):
    return {
        "id": "ally",
        "name": "Ally",
        "role": role,
        "element": element,
        "blurb": "",
        "hp": 60,
        "max_hp": 60,
        "attack": 10,
        "defense": 5,
        "credit_bonus": credit_bonus,
        "down": False,
    }


def _fight(player, companion, enemy_id="chrome_vixen"):
    stats = combat.player_stats(player)
    return combat.start(player, enemy_id, 1, stats["max_hp"], companion=companion)


# --- Companion combat behavior -------------------------------------------------


def test_companion_strikes_each_round():
    p = _player()
    state = _fight(p, _ally("dps", element="voltaic"))
    before = state["enemy_hp"]
    combat.act(p, state, "guard", rng=QuietRng())  # guard deals no damage
    assert state["enemy_hp"] < before
    assert any("Ally strikes" in line for line in state["log"])


def test_downed_companion_does_not_act():
    p = _player()
    ally = _ally("dps")
    ally["down"] = True
    state = _fight(p, ally)
    before = state["enemy_hp"]
    combat.act(p, state, "guard", rng=QuietRng())
    assert state["enemy_hp"] == before


def test_healer_heals_and_cleanses_when_hurt():
    p = _player()
    state = _fight(p, _ally("healer", element="toxin"))
    max_hp = combat.player_stats(p)["max_hp"]
    state["player_hp"] = round(max_hp * 0.3)
    state["player_effects"] = {"slow": {"turns": 3, "amount": 0}}
    hp_before = state["player_hp"]
    combat.act(p, state, "guard", rng=QuietRng())
    # Heal lands before the enemy's answer; net effect must still be positive.
    assert any("tends to you" in line for line in state["log"])
    assert any("clears the slow" in line for line in state["log"])
    assert state["player_hp"] > hp_before - 5  # healed through the enemy hit


def test_healer_attacks_when_player_is_healthy():
    p = _player()
    state = _fight(p, _ally("healer"))
    before = state["enemy_hp"]
    combat.act(p, state, "guard", rng=QuietRng())
    assert state["enemy_hp"] < before
    assert not any("tends to you" in line for line in state["log"])


def test_support_banks_an_extra_charge():
    p = _player()
    state = _fight(p, _ally("support", element="psionic"))
    combat.act(p, state, "attack", rng=QuietRng())
    # start 2, support +1, end-of-round regen +1 = 4
    assert state["charge"] == 4
    assert any("feeds your charge" in line for line in state["log"])


def test_enemy_prefers_the_tank():
    p = _player()
    ally = _ally("tank")
    state = _fight(p, ally)
    hp_before = state["player_hp"]
    combat.act(p, state, "guard", rng=TankTargetRng())
    assert state["companion"]["hp"] < ally["max_hp"]
    assert any("turns on Ally" in line for line in state["log"])
    assert state["player_hp"] == hp_before  # the hit went to the tank


def test_tank_shoulders_part_of_a_player_hit():
    p = _player()
    state = _fight(p, _ally("tank"))
    combat.act(p, state, "attack", rng=QuietRng())  # 0.99: never targets the tank
    assert any("shoulders" in line for line in state["log"])
    assert state["companion"]["hp"] < 60


def test_companion_goes_down_at_zero_hp():
    p = _player()
    ally = _ally("tank")
    ally["hp"] = 1
    state = _fight(p, ally)
    combat.act(p, state, "guard", rng=TankTargetRng())
    assert state["companion"]["down"] is True
    assert any("goes down" in line for line in state["log"])


def test_rogue_boosts_credit_drops():
    p = _player()
    state = _fight(p, _ally("rogue", credit_bonus=0.25))
    state["enemy_hp"] = 1
    before = p.credits
    combat.act(p, state, "attack", rng=QuietRng())
    assert state["victory"] is True
    expected = round(state["enemy"]["credits"] * 1.25)
    assert p.credits - before == expected


# --- Companions in the dungeon --------------------------------------------------


def _delver(companion_id=""):
    p = _player()
    p.location = dungeon.ENTRANCE_DISTRICT
    p.companion = companion_id
    return p


def test_run_materialises_the_recruited_companion():
    p = _delver("vael")
    dungeon.enter(p, GameClock(), seed=7)
    comp = p.dungeon["companion"]
    assert comp["name"] == "Vael"
    assert comp["role"] == "tank"
    assert comp["hp"] == comp["max_hp"] > 0
    assert dungeon.view(p)["companion"]["id"] == "vael"


def test_solo_run_has_no_companion():
    p = _delver()
    dungeon.enter(p, GameClock(), seed=7)
    assert p.dungeon["companion"] is None


def test_rest_room_revives_a_downed_companion():
    p = _delver("vael")
    dungeon.enter(p, GameClock(), seed=7)
    run = p.dungeon
    comp = run["companion"]
    comp["down"] = True
    comp["hp"] = 0
    room = {"content": {"type": "rest", "used": False}}
    result = dungeon._resolve_room(p, run, room, QuietRng())
    assert "patches up" in result["text"]
    assert comp["down"] is False
    assert comp["hp"] >= round(comp["max_hp"] * 0.5)


def test_leave_reports_the_companion():
    p = _delver("vael")
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    result = dungeon.leave(p, clock)
    assert result["companion"] == "vael"


# --- Curios ---------------------------------------------------------------------


def _inject_curio(p, curio_id):
    room = p.dungeon["rooms"][p.dungeon["at"]]
    room.setdefault("curios", []).append({"id": curio_id, "used": []})
    return room


def test_floors_scatter_curios():
    fd = dungeon.generate_floor(7, 1)
    placed = [c for r in fd["rooms"].values() for c in r.get("curios", [])]
    assert 2 <= len(placed) <= 3


def test_examine_is_free_and_repeatable():
    p = _delver()
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    _inject_curio(p, "warm_mannequin")
    before = clock.minute_of_day
    for _ in range(2):
        result = dungeon.curio_act(p, clock, "warm_mannequin", "examine")
        assert result["type"] == "examine"
    assert clock.minute_of_day == before


def test_verbs_cost_time_and_are_once_only():
    p = _delver()
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    _inject_curio(p, "glitter_moths")
    before_minutes = clock.minute_of_day
    before_credits = p.credits
    result = dungeon.curio_act(p, clock, "glitter_moths", "offer")
    assert clock.minute_of_day - before_minutes == dungeon.MOVE_MINUTES
    assert p.credits == before_credits + 18
    assert result["outcome"]["type"] == "credits"
    with pytest.raises(Exception, match="given what it has"):
        dungeon.curio_act(p, clock, "glitter_moths", "offer")


def test_unknown_verb_is_rejected():
    p = _delver()
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    _inject_curio(p, "glitter_moths")
    with pytest.raises(Exception):
        dungeon.curio_act(p, clock, "glitter_moths", "lick")


def test_waking_the_terminal_reveals_the_floor():
    p = _delver()
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    _inject_curio(p, "dreaming_terminal")
    dungeon.curio_act(p, clock, "dreaming_terminal", "wake")
    assert all(r["visited"] for r in p.dungeon["rooms"].values())


def test_taking_the_lipstick_grants_the_item():
    p = _delver()
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    _inject_curio(p, "lipstick_case")
    dungeon.curio_act(p, clock, "lipstick_case", "take")
    assert p.inventory.get("chrome_lipstick") == 1
    assert inventory.get_item("chrome_lipstick")["dungeon_only"] is True


def test_view_lists_curios_with_remaining_verbs():
    p = _delver()
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    _inject_curio(p, "warm_mannequin")
    curios = dungeon.view(p)["here"]["curios"]
    entry = next(c for c in curios if c["id"] == "warm_mannequin")
    assert set(entry["verbs"]) == {"touch", "kiss"}
    dungeon.curio_act(p, clock, "warm_mannequin", "touch")
    curios = dungeon.view(p)["here"]["curios"]
    entry = next(c for c in curios if c["id"] == "warm_mannequin")
    assert entry["verbs"] == ["kiss"]


# --- Party API -------------------------------------------------------------------


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    c.post("/api/travel", json={"to": "the_shallows", "mode": "walk"})
    return c


def _befriend(npc_id, amount=30):
    save_id, _, clock = save.load_models()
    social.add_opinion(save_id, npc_id, amount, 1)
    return save_id


def test_party_lists_all_candidates(client):
    body = client.get("/api/party").get_json()
    assert body["companion"] is None
    assert body["required_affection"] == dungeon.RECRUIT_AFFECTION
    ids = {c["id"] for c in body["candidates"]}
    assert {"vael", "zix", "sora", "carro", "miko"} <= ids
    assert all(not c["recruitable"] for c in body["candidates"])


def test_recruit_requires_friendship(client):
    resp = client.post("/api/party/recruit", json={"npc_id": "vael"})
    assert resp.status_code == 400
    assert "trust" in resp.get_json()["error"]
    _befriend("vael")
    resp = client.post("/api/party/recruit", json={"npc_id": "vael"})
    assert resp.status_code == 200
    assert resp.get_json()["companion"] == "vael"
    assert client.get("/api/party").get_json()["companion"] == "vael"


def test_dismiss_clears_the_companion(client):
    _befriend("sora")
    client.post("/api/party/recruit", json={"npc_id": "sora"})
    resp = client.post("/api/party/dismiss")
    assert resp.status_code == 200
    assert client.get("/api/party").get_json()["companion"] is None


def test_cannot_change_party_inside_the_substrate(client):
    _befriend("vael")
    client.post("/api/party/recruit", json={"npc_id": "vael"})
    assert client.post("/api/dungeon/enter").status_code == 200
    assert client.post("/api/party/recruit", json={"npc_id": "sora"}).status_code == 400
    assert client.post("/api/party/dismiss").status_code == 400
    client.post("/api/dungeon/leave")


def test_delving_together_builds_the_bond(client):
    _befriend("vael", 30)
    client.post("/api/party/recruit", json={"npc_id": "vael"})
    client.post("/api/dungeon/enter")
    before = next(c for c in client.get("/api/characters").get_json() if c["id"] == "vael")[
        "affection"
    ]
    resp = client.post("/api/dungeon/leave")
    body = resp.get_json()
    assert body["result"]["bond"] == 2  # floor 1: min(6, 2 + 0)
    after = next(c for c in client.get("/api/characters").get_json() if c["id"] == "vael")[
        "affection"
    ]
    assert after == before + 2


def test_companion_rides_along_in_dungeon_state(client):
    _befriend("miko")
    client.post("/api/party/recruit", json={"npc_id": "miko"})
    client.post("/api/dungeon/enter")
    run = client.get("/api/dungeon/state").get_json()["run"]
    assert run["companion"]["role"] == "support"
    assert run["companion"]["down"] is False
    client.post("/api/dungeon/leave")
