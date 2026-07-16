"""Gantry 9 — the rooftop-line terminus teahouse: always open, one cup a day
whose effect rides until midnight, and the Lookout almanac board."""

import pytest
from app import create_app
from game import actions, places, teahouse, traits, world
from game.calendar import GameClock
from game.errors import GameError
from game.player import Player


def _player(location="gantry_9", credits=100):
    p = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Drifter", trait="")
    p.location = location
    p.credits = credits
    return p


# --- The venue ---------------------------------------------------------------


def test_the_terminus_never_closes():
    assert places.district_of("gantry_9") == "the_grid"
    assert places.is_open("gantry_9", GameClock())  # 08:00
    small_hours = GameClock()
    small_hours.advance(19 * 60)  # 03:00 — the tea just gets stronger
    assert places.is_open("gantry_9", small_hours)


def test_the_avian_entry_line_is_flavor_for_a_real_trait():
    # trait_lines is pure flavor keyed by trait id — never a gate, and never
    # a typo'd key that silently shows nobody anything.
    for trait_id in places.get("gantry_9")["trait_lines"]:
        assert trait_id in traits.registry(), trait_id


# --- Tea service -------------------------------------------------------------


def test_one_cup_a_day_poured_at_the_gantry_only():
    player, clock = _player(), GameClock()
    with pytest.raises(GameError, match="chalkboard"):
        teahouse.sip(player, clock, "not_a_tea")
    away = _player(location="the_grid")
    with pytest.raises(GameError, match="Gantry 9"):
        teahouse.sip(away, clock, "kettle_lightning")

    poured = teahouse.sip(player, clock, "kettle_lightning")
    assert poured["name"] == "Kettle Lightning"
    assert player.credits == 100 - 14
    assert clock.minute_of_day == 8 * 60 + 20
    with pytest.raises(GameError, match="One cup"):
        teahouse.sip(player, clock, "petrichor_blend")


def test_kettle_lightning_quickens_walks_until_midnight():
    player, clock = _player(), GameClock()
    teahouse.sip(player, clock, "kettle_lightning")
    cost = world.travel(player, clock, "docking_quarter", "walk")
    assert cost["minutes"] == 10  # adjacent walk is normally 20

    # Next morning the hurry has worn off.
    player.location = "gantry_9"
    clock.advance(24 * 60)
    assert teahouse.active(player, clock) is None
    cost = world.travel(player, clock, "docking_quarter", "walk")
    assert cost["minutes"] == 20


def test_overclock_oolong_makes_training_stick():
    player, clock = _player(), GameClock()
    base = player.attributes["charm"]
    teahouse.sip(player, clock, "overclock_oolong")
    actions.apply_action(player, clock, "train", "charm")
    assert player.attributes["charm"] == base + 2  # 1 + steeped bonus


# --- Over the API ------------------------------------------------------------


@pytest.fixture
def client():
    c = create_app().test_client()
    c.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Drifter", "trait": ""},
    )
    return c


def _to_gantry(client):
    client.post("/api/travel", json={"to": "the_grid", "mode": "walk"})
    client.post("/api/travel", json={"to": "gantry_9", "mode": "walk"})


def test_tea_service_over_the_api(client):
    _to_gantry(client)
    res = client.post("/api/teahouse/sip", json={"tea_id": "petrichor_blend"})
    assert res.status_code == 200
    assert "argument ends well" in res.get_json()["poured"]["line"]

    state = client.get("/api/teahouse").get_json()
    assert state["sipped_today"] is True
    assert state["active"]["id"] == "petrichor_blend"
    assert client.post("/api/teahouse/sip", json={"tea_id": "petrichor_blend"}).status_code == 400


def test_petrichor_softens_the_room(client):
    _to_gantry(client)
    client.post("/api/teahouse/sip", json={"tea_id": "petrichor_blend"})
    client.post("/api/travel", json={"to": "docking_quarter", "mode": "walk"})
    for _ in range(3):  # 09:05 -> 12:05; Vex holds court from noon
        client.post("/api/action", json={"action": "wait"})
    start = client.post("/api/dialogue/start", json={"npc_id": "vex"}).get_json()
    res = client.post(
        "/api/dialogue/choose",
        json={
            "npc_id": "vex",
            "dialogue_id": start["dialogue_id"],
            "node_id": start["node"]["node_id"],
            "choice_index": 0,  # affection 2 -> the blend makes it 3
        },
    ).get_json()
    assert res["gained"] == 3


# --- The Lookout -------------------------------------------------------------


def test_the_lookout_hangs_at_the_gantry(client):
    res = client.get("/api/lookout")
    assert res.status_code == 400
    assert "Gantry 9" in res.get_json()["error"]

    _to_gantry(client)
    board = client.get("/api/lookout").get_json()
    assert {"people", "venues", "gig", "pit"} <= set(board)

    people = {p["id"]: p for p in board["people"]}
    assert people["oona"]["place"] == "The Hold"  # morning coaching
    assert people["oona"]["available"] is True

    venues = {v["id"]: v for v in board["venues"]}
    assert venues["gantry_9"]["hours"] == "always open"
    assert venues["the_pit"]["open"] is False  # first bell at 16:00

    assert board["gig"]["name"]
    assert board["pit"]["wins"] == 0
    assert board["pit"]["next_enemy"]
