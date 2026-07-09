"""Milestone 2: availability, affection, and dialogue."""

import pytest
from app import create_app
from game import dialogue, world
from game.calendar import GameClock
from game.npc import NPC


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Drifter", "pronouns": "they/them"})
    return c


class FakeClock:
    def __init__(self, minute_of_day, week=1, day=1):
        self.minute_of_day = minute_of_day
        self.week = week
        self.day = day


# --- Availability tiers -----------------------------------------------------


def _vael():
    return NPC.load("vael")


def test_available_full_early_in_window():
    # Vael decompresses at the plaza 17:00–19:00. At 17:00 there are 120 min left.
    avail = world.availability(_vael(), FakeClock(17 * 60))
    assert avail["available"] is True
    assert avail["tier"] == world.TIER_FULL
    assert avail["location"] == "citadel_plaza"


def test_shortened_and_brief_tiers():
    vael = _vael()
    # Window ends 19:00. 18:15 → 45 min left → shortened; 18:45 → 15 → brief.
    assert world.availability(vael, FakeClock(18 * 60 + 15))["tier"] == world.TIER_SHORTENED
    assert world.availability(vael, FakeClock(18 * 60 + 45))["tier"] == world.TIER_BRIEF


def test_just_missed_is_not_available():
    # 18:58 → 2 minutes left → missed glimpse, can't talk.
    avail = world.availability(_vael(), FakeClock(18 * 60 + 58))
    assert avail["tier"] == world.TIER_MISSED
    assert avail["available"] is False


def test_on_duty_window_is_unavailable():
    # 08:00–17:00 is "On duty" (available: false).
    avail = world.availability(_vael(), FakeClock(12 * 60))
    assert avail["available"] is False
    assert avail["tier"] == world.TIER_UNAVAILABLE


def test_window_crossing_midnight():
    # Vael's home window is 22:00–06:00 (available: false). 02:00 falls inside it.
    avail = world.availability(_vael(), FakeClock(2 * 60))
    assert avail["available"] is False
    assert avail["tier"] == world.TIER_UNAVAILABLE


# --- Pronoun helper ---------------------------------------------------------


def test_render_pronouns_presets():
    text = "{Subj} took {pos} coat. That's {pos_pron}."
    she = dialogue.render_pronouns(text, pronouns="she/her")
    they = dialogue.render_pronouns(text, pronouns="they/them")
    assert she == "She took her coat. That's hers."
    assert they == "They took their coat. That's theirs."


def test_render_pronouns_custom_fallback():
    out = dialogue.render_pronouns("{subj}/{obj}", pronouns="ey/em")
    assert out == "ey/em"


# --- Dialogue via the API ---------------------------------------------------


def _make_available(client):
    """Get the player to Vael: travel to the Citadel Ring, then advance to her
    plaza window (17:00–19:00, full tier)."""
    client.post("/api/travel", json={"to": "citadel_ring", "mode": "walk"})
    for _ in range(12):
        clock = client.get("/api/game/state").get_json()["clock"]
        if 17 * 60 <= clock["minute_of_day"] < 18 * 60:
            break
        client.post("/api/action", json={"action": "wait"})


def test_cannot_talk_when_unavailable(client):
    # Still 08:00 → Vael is on duty.
    resp = client.post("/api/dialogue/start", json={"npc_id": "vael"})
    assert resp.status_code == 400
    assert "available" in resp.get_json()["error"].lower()


def test_full_conversation_gains_affection(client):
    _make_available(client)
    start = client.post("/api/dialogue/start", json={"npc_id": "vael"}).get_json()
    assert start["tier"] == world.TIER_FULL
    node = start["node"]
    assert node["node_id"] == "n1"

    # Choose the plain (ungated) first option: +2 affection, → n2.
    step = client.post(
        "/api/dialogue/choose",
        json={"npc_id": "vael", "node_id": "n1", "choice_index": 0},
    ).get_json()
    assert step["gained"] == 2
    assert step["ended"] is False

    # Finish at n5 with "I will." (+2), which ends the conversation.
    end = client.post(
        "/api/dialogue/choose",
        json={"npc_id": "vael", "node_id": "n5", "choice_index": 0},
    ).get_json()
    assert end["ended"] is True
    assert end["affection"] == 4  # 2 + 2


def test_one_conversation_per_day(client):
    _make_available(client)
    first = client.post("/api/dialogue/start", json={"npc_id": "vael"})
    assert first.status_code == 200
    second = client.post("/api/dialogue/start", json={"npc_id": "vael"})
    assert second.status_code == 400
    assert "today" in second.get_json()["error"].lower()


def test_stat_gated_choice_is_locked_for_low_stats(client):
    _make_available(client)
    start = client.post("/api/dialogue/start", json={"npc_id": "vael"}).get_json()
    charm_choice = start["node"]["choices"][1]  # the [Charm] option
    assert charm_choice["locked"] is True
    assert charm_choice["requires"] == {"charm": 6}

    # Attempting the locked choice is rejected.
    resp = client.post(
        "/api/dialogue/choose",
        json={"npc_id": "vael", "node_id": "n1", "choice_index": 1},
    )
    assert resp.status_code == 400


def test_affection_persists_and_shows_in_characters(client):
    _make_available(client)
    client.post("/api/dialogue/start", json={"npc_id": "vael"})
    client.post(
        "/api/dialogue/choose",
        json={"npc_id": "vael", "node_id": "n1", "choice_index": 0},
    )
    chars = client.get("/api/characters").get_json()
    vael = next(c for c in chars if c["id"] == "vael")
    assert vael["affection"] == 2
    assert vael["talked_today"] is True
    assert vael["availability"]["available"] is True


def test_tier_multipliers_scale_affection():
    # A +2 choice yields 2 at full, 1 at shortened (×0.6), 1 at brief (×0.3),
    # and 0 when just missed.
    assert round(2 * world.TIER_MULTIPLIER[world.TIER_FULL]) == 2
    assert round(2 * world.TIER_MULTIPLIER[world.TIER_SHORTENED]) == 1
    assert round(2 * world.TIER_MULTIPLIER[world.TIER_BRIEF]) == 1
    assert round(2 * world.TIER_MULTIPLIER[world.TIER_MISSED]) == 0


def test_clock_rollover_gives_new_conversation_day():
    a = GameClock(week=1, day=1)
    b = GameClock(week=1, day=2)
    assert (a.week - 1) * 7 + a.day != (b.week - 1) * 7 + b.day
