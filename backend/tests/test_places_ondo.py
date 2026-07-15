"""Places (districts + venues), venue travel, and Ondo "The Bell" Marr — the
Pit's founder, master of ceremonies, and ninth member of the cast."""

import pytest
from app import create_app
from game import dialogue, places, world
from game.calendar import GameClock
from game.errors import GameError
from game.npc import NPC
from game.player import Player


def _player(location="the_grid"):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.location = location
    return p


def _evening():
    clock = GameClock()
    clock.advance(9 * 60)  # 08:00 -> 17:00, inside the Pit's hours
    return clock


# --- The place model -----------------------------------------------------------------


def test_a_venue_is_a_place_inside_a_district():
    assert places.is_venue("the_pit")
    assert not places.is_venue("the_grid")
    assert places.district_of("the_pit") == "the_grid"
    assert places.district_of("the_grid") == "the_grid"
    assert places.get("the_pit")["name"] == "The Pit"
    assert "the_pit" in places.venues_in("the_grid")
    assert places.venues_in("docking_quarter") == {}


def test_venue_hours_cross_midnight():
    clock = GameClock()  # 08:00 — chained hatch
    assert not places.is_open("the_pit", clock)
    assert places.is_open("the_pit", _evening())
    late = GameClock()
    late.advance(18 * 60)  # 02:00 next morning — still going
    assert places.is_open("the_pit", late)
    assert places.is_open("the_grid", clock)  # districts never close


# --- Venue travel ---------------------------------------------------------------------


def test_stepping_into_a_venue_is_a_local_hop():
    p = _player("the_grid")
    cost = world.travel(p, _evening(), "the_pit", "walk")
    assert cost["distance"] == "local"
    assert cost["minutes"] == 5
    assert p.location == "the_pit"
    # Stepping back out is local too.
    assert world.travel(p, _evening(), "the_grid", "walk")["distance"] == "local"
    assert p.location == "the_grid"


def test_closed_venues_turn_you_away():
    p = _player("the_grid")
    with pytest.raises(GameError, match="FIRST BELL AT 16:00"):
        world.travel(p, GameClock(), "the_pit", "walk")
    assert p.location == "the_grid"


def test_district_travel_resolves_from_a_venues_parent():
    p = _player("the_pit")
    # The Grid and the Docking Quarter are adjacent; leaving from inside the
    # Pit prices the leg from the Grid, not from some nowhere.
    cost = world.travel(p, _evening(), "docking_quarter", "walk")
    assert cost["distance"] == "adjacent"
    assert p.location == "docking_quarter"


def test_entering_a_venue_from_another_district_prices_the_district_leg():
    p = _player("docking_quarter")
    cost = world.travel(p, _evening(), "the_pit", "transit")
    assert cost["distance"] == "adjacent"
    assert p.location == "the_pit"


# --- Ondo, the pit master ---------------------------------------------------------------


def test_ondo_is_a_full_cast_member():
    ondo = NPC.load("ondo")
    assert ondo.romanceable
    assert ondo.pronouns == "they/them"
    assert ondo.district == "the_grid"
    assert ondo.unlocked_for(_player())  # present from day one — no defeat gate
    # Ringside during fight hours, in the venue itself.
    ringside = ondo.schedule[0]
    assert ringside["district"] == "the_pit"
    assert (ringside["start"], ringside["end"]) == ("16:00", "04:00")


def test_ondo_is_reachable_only_inside_the_pit():
    ondo = NPC.load("ondo")
    avail = world.availability(ondo, _evening())
    assert avail["available"] is True
    assert avail["district"] == "the_pit"  # == player.location only in the venue
    morning = world.availability(ondo, GameClock())
    assert morning["available"] is False


def test_ondos_companion_is_gated_on_beating_them():
    spec = NPC.load("ondo").companion
    assert spec["role"] == "tank"
    assert spec["requires_event"] == "defeated:ondo_the_bell"


# --- Event-gated dialogue ---------------------------------------------------------------


def _ondo_node(node_id, player):
    tree = dialogue.tree_by_id("ondo_intro")
    return dialogue.node_view(tree, node_id, player)


def test_the_retirement_answer_hides_until_youve_beaten_them():
    p = _player()
    texts = [c["text"] for c in _ondo_node("n5", p)["choices"]]
    assert not any("other side of the bell" in t for t in texts)
    # Choosing it blind is refused, not just hidden.
    tree = dialogue.tree_by_id("ondo_intro")
    with pytest.raises(GameError, match="requirement"):
        dialogue.resolve_choice(tree, "n5", 1, p)

    p.fired_events.append("defeated:ondo_the_bell")
    view = _ondo_node("n5", p)
    unlocked = [c for c in view["choices"] if "other side of the bell" in c["text"]]
    assert unlocked and unlocked[0]["index"] == 1  # original index survives hiding
    next_id, choice = dialogue.resolve_choice(tree, "n5", 1, p)
    assert next_id == "n_answer"
    assert choice["affection"] == 5


# --- API ---------------------------------------------------------------------------------


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    return c


def _to_the_pit(client):
    for _ in range(8):  # 08:00 -> 16:00
        client.post("/api/action", json={"action": "wait"})
    client.post("/api/travel", json={"to": "the_grid", "mode": "walk"})
    return client.post("/api/travel", json={"to": "the_pit", "mode": "walk"})


def test_venues_api_lists_the_pit(client):
    body = client.get("/api/venues").get_json()
    assert body["the_pit"]["district"] == "the_grid"
    assert body["the_pit"]["hours"] == {"open": "16:00", "close": "04:00"}


def test_ondo_reachability_via_api(client):
    _to_the_pit(client)
    cast = {c["id"]: c for c in client.get("/api/characters").get_json()}
    assert cast["ondo"]["reachable"] is True
    # Step out: the pit master doesn't follow you upstairs.
    client.post("/api/travel", json={"to": "the_grid", "mode": "walk"})
    cast = {c["id"]: c for c in client.get("/api/characters").get_json()}
    assert cast["ondo"]["reachable"] is False
    resp = client.post("/api/dialogue/start", json={"npc_id": "ondo"})
    assert resp.status_code == 400
    assert "The Pit" in resp.get_json()["error"]


def test_ondos_companion_is_locked_via_api_until_the_founders_bout(client):
    from game import save

    body = client.get("/api/party").get_json()
    ondo = next(c for c in body["candidates"] if c["id"] == "ondo")
    assert ondo["locked"] is True
    assert ondo["recruitable"] is False
    assert "stood across from" in ondo["blurb"]

    save_id, player, clock = save.load_models()
    resp = client.post("/api/party/recruit", json={"npc_id": "ondo"})
    assert resp.status_code == 400
    assert "stood across from" in resp.get_json()["error"]

    player.fired_events.append("defeated:ondo_the_bell")
    save.save_models(save_id, player, clock)
    body = client.get("/api/party").get_json()
    ondo = next(c for c in body["candidates"] if c["id"] == "ondo")
    assert ondo["locked"] is False
    assert "step in front of you" in ondo["blurb"]
