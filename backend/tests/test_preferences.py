"""Preferences, compatibility, discovery, and memory decay."""

import pytest
from app import create_app
from game import preferences, social
from game.npc import NPC


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    return c


def _make_available(client):
    # Travel to Vael's district, then advance to her plaza window (full tier).
    client.post("/api/travel", json={"to": "citadel_ring", "mode": "walk"})
    for _ in range(12):
        clock = client.get("/api/game/state").get_json()["clock"]
        if 17 * 60 <= clock["minute_of_day"] < 18 * 60:
            break
        client.post("/api/action", json={"action": "wait"})


# --- Preference data --------------------------------------------------------


def test_player_has_default_preferences(client):
    player = client.get("/api/game/state").get_json()["player"]
    assert player["preferences"]["books"]["sentiment"] == "love"
    assert player["preferences"]["nightlife"]["sentiment"] == "dislike"


def test_vael_preferences_load_with_changeable_flags():
    vael = NPC.load("vael")
    assert vael.preferences["books"]["sentiment"] == "love"
    assert vael.preferences["fitness"]["changeable"] is False  # core, unchangeable
    assert vael.preferences["books"]["changeable"] is True     # defaults from topic


def test_relationships_start_neutral(client):
    vael = _character(client, "vael")
    assert vael["affection"] == 0  # neutral starting disposition


# --- Compatibility (asymmetric) ---------------------------------------------


def test_compatibility_is_asymmetric():
    # Opposition hurts, scaled by intensity.
    assert preferences.compatibility_delta("love", "hate") == -4
    assert preferences.compatibility_delta("like", "dislike") == -1
    # Merely sharing a like gives nothing; sharing a strong feeling gives +1.
    assert preferences.compatibility_delta("love", "like") == 0
    assert preferences.compatibility_delta("love", "love") == 1
    # Neutral on either side is neutral.
    assert preferences.compatibility_delta("love", "neutral") == 0


# --- Discovery / hidden knowledge -------------------------------------------


def test_npc_preferences_are_hidden_until_discovered(client):
    vael = _character(client, "vael")
    # Nothing discovered yet → no visible preferences.
    assert vael["preferences"] == {}


def test_discovery_reveals_one_topic(client):
    _make_available(client)
    client.post("/api/dialogue/start", json={"npc_id": "vael"})
    # n2 choice 2 reveals Vael's stance on books.
    client.post(
        "/api/dialogue/choose",
        json={"npc_id": "vael", "node_id": "n2", "choice_index": 2},
    )
    vael = _character(client, "vael")
    assert vael["preferences"]["books"]["sentiment"] == "love"
    # Other preferences stay hidden.
    assert "nightlife" not in vael["preferences"]


# --- Memory decay + severity + early amplification --------------------------


def test_offense_hits_harder_early(client):
    _make_available(client)
    client.post("/api/dialogue/start", json={"npc_id": "vael"})
    # n1 choice 3 is a moderate offense (base -4). At neutral, amplified ~2x.
    res = client.post(
        "/api/dialogue/choose",
        json={"npc_id": "vael", "node_id": "n1", "choice_index": 3},
    ).get_json()
    assert res["affection"] == -8  # -4 * 2.0 early amplification
    assert res["gained"] == -8
    # It routes to a cold closing node.
    assert res["node"]["node_id"] == "n_cold"


def test_minor_offense_decays_over_time():
    # A minor offense fully fades over its window (7 days).
    memories = [{"day": 0, "delta": -6, "decays": True, "severity": "minor"}]
    assert social._affection_from(0, memories, today=0) == -6
    assert social._affection_from(0, memories, today=4) == pytest.approx(-2, abs=1)
    assert social._affection_from(0, memories, today=7) == 0
    assert social._affection_from(0, memories, today=99) == 0


def test_severe_offense_never_decays():
    memories = [{"day": 0, "delta": -10, "decays": False, "severity": "severe"}]
    assert social._affection_from(0, memories, today=0) == -10
    assert social._affection_from(0, memories, today=999) == -10


def test_positive_memories_are_permanent():
    memories = [{"day": 0, "delta": 5, "decays": False}]
    assert social._affection_from(0, memories, today=999) == 5


def test_affection_is_clamped():
    memories = [{"day": 0, "delta": 500, "decays": False}]
    assert social._affection_from(0, memories, today=0) == social.MAX_AFFECTION


# --- helpers ----------------------------------------------------------------


def _character(client, npc_id):
    chars = client.get("/api/characters").get_json()
    return next(c for c in chars if c["id"] == npc_id)
