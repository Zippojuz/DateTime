"""The Tide Line — the flooded maintenance levels, passable only at slack
water (04:00–06:00): salvage runs on the event table, and Ondo's dawn walk
made real (a place-keyed dialogue ringside can't offer)."""

import random

import pytest
from app import create_app
from game import data, dialogue, places, salvage, save, social, world
from game.calendar import GameClock
from game.errors import GameError
from game.npc import NPC
from game.player import Player


def _player(location="the_tide_line"):
    p = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Drifter", trait="")
    p.location = location
    return p


def _slack_water():
    clock = GameClock()
    clock.advance(20 * 60 + 30)  # 08:00 + 20h30 = 04:30 next day
    return clock


# --- The venue ---------------------------------------------------------------


def test_the_hatch_opens_only_at_slack_water():
    assert places.district_of("the_tide_line") == "docking_quarter"
    assert not places.is_open("the_tide_line", GameClock())  # 08:00
    assert places.is_open("the_tide_line", _slack_water())
    just_missed = GameClock()
    just_missed.advance(22 * 60)  # 06:00 sharp — the sea has opinions again
    assert not places.is_open("the_tide_line", just_missed)


def test_the_event_table_is_well_formed():
    cfg = data.load("tide_line")
    items = data.load("items")
    assert places.is_venue(cfg["venue"])
    for event in cfg["events"]:
        assert event["weight"] > 0 and event["text"]
        for iid in event.get("items", []):
            assert iid in items, iid
        if "item" in event:
            assert event["item"] in items


# --- Salvage runs --------------------------------------------------------------


def test_a_run_costs_cold_minutes_and_rolls_the_table():
    p, clock = _player(), _slack_water()
    result = salvage.run(p, clock, rng=random.Random(7))
    assert result["id"] in {e["id"] for e in data.load("tide_line")["events"]}
    assert p.energy == 92
    assert clock.minute_of_day == 5 * 60  # 04:30 + 30m

    with pytest.raises(GameError, match="DO NOT ARGUE WITH THE SEA"):
        salvage.run(_player(), GameClock())
    with pytest.raises(GameError, match="find the hatch"):
        salvage.run(_player(location="docking_quarter"), _slack_water())


def test_each_event_resolves_its_effects():
    events = {e["id"]: e for e in data.load("tide_line")["events"]}
    rng = random.Random(0)

    p = _player()
    out = salvage._resolve(p, events["flotsam"], rng)
    lo, hi = events["flotsam"]["credits"]
    assert lo <= out["credits"] <= hi
    assert p.credits == 50 + out["credits"]

    p = _player()
    out = salvage._resolve(p, events["sealed_crate"], rng)
    assert p.inventory[out["item"]] == 1 and out["item_name"]

    p = _player()
    p.energy = 50
    out = salvage._resolve(p, events["cold_surge"], rng)
    assert p.energy == 40 and out["energy"] == -10

    p = _player()
    out = salvage._resolve(p, events["tide_glass"], rng)
    assert p.inventory["tide_glass"] == 1

    p = _player()
    before = dict(p.inventory)
    out = salvage._resolve(p, events["the_far_figure"], rng)
    assert "walking the water line" in out["text"]
    assert p.credits == 50 and p.inventory == before  # they never look your way


# --- Ondo's dawn walk ------------------------------------------------------------


def test_ondo_walks_the_water_line_at_dawn():
    ondo = NPC.load("ondo")
    av = world.availability(ondo, _slack_water())
    assert av["available"] is True
    assert av["district"] == "the_tide_line"
    asleep = GameClock()  # 08:00 — the bell can wait
    assert world.availability(ondo, asleep)["available"] is False


def test_the_dawn_conversation_is_keyed_to_place_and_warmth():
    # Ringside (or anywhere else): the intro, as ever.
    assert dialogue.tree_for_npc("ondo", 20, location="the_pit")["id"] == "ondo_intro"
    # At the water line, a stranger gets the brush-off...
    assert dialogue.tree_for_npc("ondo", 0, location="the_tide_line")["id"] == "ondo_dawn_cold"
    # ...and someone who's earned it gets the walk.
    assert dialogue.tree_for_npc("ondo", 12, location="the_tide_line")["id"] == "ondo_dawn"


def test_the_bell_branch_stays_hidden_until_the_founders_bout():
    p = _player()
    tree = dialogue.tree_by_id("ondo_dawn")
    texts = [c["text"] for c in dialogue.node_view(tree, "n4", p)["choices"]]
    assert not any("other side of your bell" in t for t in texts)
    p.fired_events.append("defeated:ondo_the_bell")
    texts = [c["text"] for c in dialogue.node_view(tree, "n4", p)["choices"]]
    assert any("other side of your bell" in t for t in texts)


# --- Over the API -----------------------------------------------------------------


@pytest.fixture
def client():
    c = create_app().test_client()
    c.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Drifter", "trait": ""},
    )
    return c


def _to_slack_water(client):
    """Set the clock to 04:30 and stand at the hatch."""
    save_id, player, clock = save.load_models()
    clock.advance(20 * 60 + 30)
    save.save_models(save_id, player, clock)
    client.post("/api/travel", json={"to": "docking_quarter", "mode": "walk"})
    client.post("/api/travel", json={"to": "the_tide_line", "mode": "walk"})


def test_salvage_and_the_dawn_walk_via_api(client):
    # Warm Ondo past the threshold first (the walk is earned, not stumbled into).
    save_id, player, clock = save.load_models()
    social.add_opinion(save_id, "ondo", 14, 1)
    save.save_models(save_id, player, clock)

    _to_slack_water(client)
    res = client.post("/api/salvage", json={})
    assert res.status_code == 200
    assert res.get_json()["salvage"]["text"]

    start = client.post("/api/dialogue/start", json={"npc_id": "ondo"})
    assert start.status_code == 200
    body = start.get_json()
    assert body["dialogue_id"] == "ondo_dawn"
    assert "the first one who followed" in body["node"]["text"]
