"""The species registry (suggestions, never gates), the Hold (the Docking
Quarter's gym venue), house training rates, and Oona the head coach."""

import pytest
from app import create_app
from game import data, dialogue, places, world
from game.actions import ACTIONS, apply_action, house_rates
from game.calendar import GameClock
from game.npc import NPC
from game.player import Player


def _player(location="the_hold"):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.location = location
    return p


# --- Species: a registry of suggestions, never a gate -----------------------------------


def test_species_registry_offers_suggestions():
    registry = data.load("species")
    assert "human" in registry and "uplift" in registry
    for entry in registry.values():
        assert entry["name"] and entry["blurb"]


def test_player_species_is_free_text():
    # Registry names work; so does anything else. Identity is data, not a gate.
    named = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Warform")
    assert named.species == "Warform"
    custom = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Sentient fog (rude)")
    assert custom.species == "Sentient fog (rude)"
    default = Player.create({"name": "Kai", "pronouns": "she/her"})
    assert default.species == "human"


# --- The Hold: gym venue + house rates ---------------------------------------------------


def test_the_hold_is_a_docking_quarter_venue_with_hours():
    assert "the_hold" in places.venues_in("docking_quarter")
    assert places.district_of("the_hold") == "docking_quarter"
    early = GameClock()
    early.advance(-3 * 60 % (24 * 60))  # 05:00
    assert not places.is_open("the_hold", early)
    assert places.is_open("the_hold", GameClock())  # 08:00 — doors open at 06:00


def test_house_rates_apply_to_coached_attributes_only():
    at_gym = _player("the_hold")
    assert house_rates(at_gym, "agility")["energy"] == -8
    assert house_rates(at_gym, "courage") is not None
    assert house_rates(at_gym, "charm") is None  # find that in a bar
    assert house_rates(_player("docking_quarter"), "agility") is None


def test_training_at_the_gym_is_faster_and_cheaper():
    p = _player("the_hold")
    clock = GameClock()
    apply_action(p, clock, "train", "agility")
    assert p.energy == 100 - 8
    assert clock.minute_of_day == 8 * 60 + 60  # one hour, not two
    assert p.attributes["agility"] == 6

    street = _player("docking_quarter")
    street_clock = GameClock()
    apply_action(street, street_clock, "train", "agility")
    assert street.energy == 100 + ACTIONS["train"]["energy"]
    assert street_clock.minute_of_day == 8 * 60 + ACTIONS["train"]["minutes"]


def test_gym_coaching_doesnt_discount_book_learning():
    p = _player("the_hold")
    clock = GameClock()
    apply_action(p, clock, "train", "wit")
    assert p.energy == 100 + ACTIONS["train"]["energy"]  # full price off the floor


# --- Oona ---------------------------------------------------------------------------------


def test_oona_is_a_full_cast_member():
    oona = NPC.load("oona")
    assert oona.romanceable
    assert oona.pronouns == "she/her"
    assert "octopus" in oona.species.lower()
    assert oona.district == "docking_quarter"
    assert oona.companion["role"] == "support"
    # Coaching from inside the venue; tank hours are private.
    floors = [w for w in oona.schedule if w.get("available")]
    assert floors and all(w["district"] == "the_hold" for w in floors)


def test_oona_keeps_tank_hours():
    lunch = GameClock()
    lunch.advance(6 * 60)  # 14:00 — in the tank, do not knock
    avail = world.availability(NPC.load("oona"), lunch)
    assert avail["available"] is False
    morning = world.availability(NPC.load("oona"), GameClock())
    assert morning["available"] is True
    assert morning["district"] == "the_hold"


def test_oona_has_an_intro_tree():
    tree = dialogue.tree_for_npc("oona")
    assert tree["id"] == "oona_intro"
    # The lab-escape node reveals her fitness preference on the right choice.
    n4 = tree["nodes"]["n4"]
    assert any(c.get("reveal_npc") == "fitness" for c in n4["choices"])


# --- API -----------------------------------------------------------------------------------


@pytest.fixture
def app_client():
    return create_app().test_client()


def test_species_api_and_creation_flow(app_client):
    registry = app_client.get("/api/species").get_json()
    assert registry["uplift"]["name"] == "Uplift"

    res = app_client.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Feathered Avian"},
    )
    assert res.status_code == 201
    assert res.get_json()["player"]["species"] == "Feathered Avian"

    # Omitting species keeps the old default.
    res = app_client.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    assert res.get_json()["player"]["species"] == "human"


def test_gym_flow_via_api(app_client):
    app_client.post(
        "/api/game/new", json={"name": "Kai", "pronouns": "she/her", "species": "Uplift"}
    )
    resp = app_client.post("/api/travel", json={"to": "the_hold", "mode": "walk"})
    assert resp.status_code == 200
    assert resp.get_json()["state"]["player"]["location"] == "the_hold"

    cast = {c["id"]: c for c in app_client.get("/api/characters").get_json()}
    assert cast["oona"]["reachable"] is True

    before = app_client.get("/api/game/state").get_json()["player"]
    body = app_client.post(
        "/api/action", json={"action": "train", "attribute": "agility"}
    ).get_json()
    assert body["player"]["energy"] == before["energy"] - 8
    assert body["player"]["attributes"]["agility"] == before["attributes"]["agility"] + 1
