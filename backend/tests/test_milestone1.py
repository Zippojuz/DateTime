"""Milestone 1: player creation, the daily loop, transformation locks."""

import pytest
from app import create_app
from game.calendar import GameClock
from game.character import Character
from game.npc import NPC
from game.player import Player


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    # Reset the single save between tests.
    c.post("/api/game/new", json={"name": "Reset"})
    return c


def _new(client, **identity):
    identity.setdefault("name", "Drifter")
    return client.post("/api/game/new", json=identity).get_json()


# --- Creation ---------------------------------------------------------------


def test_new_game_defaults_to_human_with_registry_attributes(client):
    state = _new(client, name="Kai", pronouns="she/her")
    player = state["player"]
    assert player["species"] == "human"
    assert player["energy"] == 100
    # Attributes come from the registry defaults.
    assert player["attributes"] == {
        "charm": 5,
        "wit": 5,
        "courage": 5,
        "empathy": 5,
        "agility": 5,
        "luck": 5,
        "hacking": 5,
    }
    # Identity is locked: current == created at creation.
    assert player["identity"] == player["created_identity"]
    assert player["identity"]["name"] == "Kai"
    assert player["identity"]["pronouns"] == "she/her"
    assert player["unlocked_transformations"] == []


def test_new_game_requires_a_name(client):
    resp = client.post("/api/game/new", json={"name": "   "})
    assert resp.status_code == 400


def test_state_persists_and_reloads(client):
    _new(client, name="Echo")
    state = client.get("/api/game/state").get_json()
    assert state["player"]["identity"]["name"] == "Echo"
    assert state["clock"]["time"] == "08:00"


# --- Daily loop -------------------------------------------------------------


def test_wait_advances_the_clock(client):
    _new(client)
    state = client.post("/api/action", json={"action": "wait"}).get_json()
    assert state["clock"]["time"] == "09:00"


def test_explore_costs_energy_and_time(client):
    _new(client)
    state = client.post("/api/action", json={"action": "explore"}).get_json()
    assert state["player"]["energy"] == 90
    assert state["clock"]["time"] == "09:00"


def test_rest_restores_energy_and_rolls_the_day(client):
    _new(client)
    client.post("/api/action", json={"action": "explore"})  # drop to 90
    state = client.post("/api/action", json={"action": "rest"}).get_json()
    assert state["player"]["energy"] == 100
    # 09:00 + 8h = 17:00, same day.
    assert state["clock"]["time"] == "17:00"


def test_train_raises_the_chosen_attribute(client):
    _new(client)
    state = client.post("/api/action", json={"action": "train", "attribute": "wit"}).get_json()
    assert state["player"]["attributes"]["wit"] == 6
    assert state["player"]["energy"] == 85


def test_train_requires_a_valid_attribute(client):
    _new(client)
    resp = client.post("/api/action", json={"action": "train", "attribute": "nope"})
    assert resp.status_code == 400


def test_too_tired_is_rejected(client):
    _new(client)
    # Drain energy with repeated training (15 each) until the next one fails.
    last = None
    for _ in range(10):
        last = client.post("/api/action", json={"action": "train", "attribute": "charm"})
    assert last.status_code == 400
    assert "tired" in last.get_json()["error"].lower()


def test_unknown_action_is_rejected(client):
    _new(client)
    resp = client.post("/api/action", json={"action": "teleport"})
    assert resp.status_code == 400


def test_day_and_week_roll_over(client):
    _new(client)
    clock = GameClock()
    clock.advance(24 * 60 * 8)  # 8 days
    assert clock.week == 2
    assert clock.day == 2


# --- Transformation (locked at creation) ------------------------------------


def test_transform_is_locked_at_creation(client):
    _new(client)
    # Outside the clinic, the location gate answers first.
    resp = client.post("/api/player/transform", json={"changes": {"pronouns": "he/him"}})
    assert resp.status_code == 400
    assert "second skin" in resp.get_json()["error"].lower()
    # At the clinic, the story lock still holds until Juno unlocks the aspect.
    client.post("/api/travel", json={"to": "the_grid", "mode": "walk"})
    resp = client.post("/api/player/transform", json={"changes": {"pronouns": "he/him"}})
    assert resp.status_code == 400
    assert "unlocked" in resp.get_json()["error"].lower()


def test_transform_rejects_immutable_aspects():
    player = Player.create({"name": "Vex", "pronouns": "they/them"})
    player.unlocked_transformations = ["pronouns"]
    with pytest.raises(Exception):
        player.transform({"name": "NewName"})


def test_transform_works_once_unlocked():
    player = Player.create({"name": "Vex", "pronouns": "they/them"})
    player.unlocked_transformations = ["pronouns"]
    player.transform({"pronouns": "she/her"})
    assert player.current_identity["pronouns"] == "she/her"
    # The locked snapshot is untouched.
    assert player.created_identity["pronouns"] == "they/them"


# --- Shared model hierarchy -------------------------------------------------


def test_player_and_npc_are_characters():
    player = Player.create({"name": "Kai"})
    assert isinstance(player, Character)
    assert player.name == "Kai"
    assert isinstance(NPC.load("vael"), Character)


# --- NPC model (subclasses Character; mirrors the player's attributes) -------


def test_npc_attributes_mirror_the_registry():
    npc = NPC.from_data({"id": "x", "name": "Vael"})  # no overrides
    assert npc.attributes == {
        "charm": 5,
        "wit": 5,
        "courage": 5,
        "empathy": 5,
        "agility": 5,
        "luck": 5,
        "hacking": 5,
    }


def test_npc_overrides_merge_over_defaults():
    npc = NPC.from_data({"id": "x", "name": "Vael", "attributes": {"courage": 12}})
    assert npc.attributes["courage"] == 12
    assert npc.attributes["charm"] == 5  # untouched default


def test_npc_loads_from_characters_json():
    vael = NPC.load("vael")
    assert vael.name == "Vael"
    assert vael.pronouns == "she/her"
    assert vael.species == "Bioluminescent tall being"
    assert vael.romanceable is True
    assert len(vael.schedule) > 0
    # Mirrors the registry attribute set since Vael has no overrides.
    assert set(vael.attributes) == {
        "charm",
        "wit",
        "courage",
        "empathy",
        "agility",
        "luck",
        "hacking",
    }


def test_npc_load_unknown_raises():
    with pytest.raises(KeyError):
        NPC.load("nobody")


def test_load_all_npcs():
    npcs = NPC.load_all()
    assert "vael" in npcs
    assert all(isinstance(n, NPC) for n in npcs.values())
