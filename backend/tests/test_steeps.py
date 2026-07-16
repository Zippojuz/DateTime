"""The Steeps — bathhouse in a dead cooling tower: the paid soak, and THE
DATING SYSTEM (venue-keyed outing scenes, choice beats, topic-modulated
affection, once per NPC per week)."""

import pytest
from app import create_app
from game import bathhouse, data, dating, places, save, social
from game.calendar import GameClock
from game.errors import GameError
from game.npc import NPC
from game.player import Player


def _player(location="the_steeps", credits=500):
    p = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Drifter", trait="")
    p.location = location
    p.credits = credits
    return p


def _midday():
    clock = GameClock()
    clock.advance(4 * 60)  # 12:00 — pools open at 10:00
    return clock


# --- The venue + the soak ------------------------------------------------------


def test_the_pools_keep_bathhouse_hours():
    assert places.district_of("the_steeps") == "bloom_district"
    assert not places.is_open("the_steeps", GameClock())  # 08:00: barred
    assert places.is_open("the_steeps", _midday())
    late = GameClock()
    late.advance(17 * 60)  # 01:00 — still steaming
    assert places.is_open("the_steeps", late)


def test_a_soak_is_fast_paid_sleep():
    p, clock = _player(), _midday()
    p.energy = 20
    result = bathhouse.soak(p, clock)
    assert p.energy == 100
    assert p.credits == 500 - 25
    assert clock.minute_of_day == 13 * 60 + 30
    assert "forgiven you" in result["line"]

    with pytest.raises(GameError, match="POOLS OPEN AT 10:00"):
        bathhouse.soak(_player(), GameClock())
    with pytest.raises(GameError, match="Bloom District"):
        bathhouse.soak(_player(location="bloom_district"), _midday())
    broke = _player()
    broke.credits = 5
    with pytest.raises(GameError, match="isn't free"):
        bathhouse.soak(broke, _midday())


# --- Scene data integrity --------------------------------------------------------


def test_every_date_scene_is_playable():
    for vid, scene in dating.scenes().items():
        assert places.is_venue(vid), f"{vid} isn't a place"
        assert scene["venue"] == vid
        assert scene["beats"], f"{vid} has no beats"
        for beat in scene["beats"]:
            assert beat["choices"], "a beat with no choices"
            # Every beat keeps a topic-free choice — the date never hinges
            # on guessing someone's preferences right.
            assert any("topic" not in c for c in beat["choices"])
            for c in beat["choices"]:
                assert c["text"] and "reply" in c
                if "topic" in c:
                    assert c["topic"] in data.load("topics"), c["topic"]
        assert scene["closing_good"] and scene["closing_flat"]


# --- Asking someone out -----------------------------------------------------------


@pytest.fixture
def client():
    c = create_app().test_client()
    c.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Drifter", "trait": ""},
    )
    return c


def _warm_up_oona(client, affection=15):
    """Meet Oona at the Hold and set the bond by hand."""
    client.post("/api/travel", json={"to": "the_hold", "mode": "walk"})
    client.post("/api/dialogue/start", json={"npc_id": "oona"})
    save_id, player, clock = save.load_models()
    day = (clock.week - 1) * 7 + clock.day
    current = social.get_affection(save_id, "oona", day)
    social.add_opinion(save_id, "oona", affection - current, day)
    player.credits = max(player.credits, 200)  # dates aren't cheap; fund the tester
    save.save_models(save_id, player, clock)


def test_you_ask_in_person_and_strangers_say_no(client):
    # Oona is reachable at the Hold, but you're not there.
    res = client.post("/api/date/start", json={"npc_id": "oona", "venue": "the_steeps"})
    assert res.status_code == 400
    assert "in person" in res.get_json()["error"]

    # There, but barely acquainted (a stranger, affection < 10).
    client.post("/api/travel", json={"to": "the_hold", "mode": "walk"})
    client.post("/api/dialogue/start", json={"npc_id": "oona"})
    res = client.post("/api/date/start", json={"npc_id": "oona", "venue": "the_steeps"})
    assert res.status_code == 400
    assert "Ask me again when we do" in res.get_json()["error"]


def test_a_full_date_at_the_steeps(client):
    _warm_up_oona(client)
    for _ in range(2):  # 10:00 — the pools open
        client.post("/api/action", json={"action": "wait"})

    res = client.post("/api/date/start", json={"npc_id": "oona", "venue": "the_steeps"})
    assert res.status_code == 200
    body = res.get_json()
    beat = body["date"]
    assert beat["title"] == "A soak at the Steeps"
    assert "good call" in beat["opening"]
    assert beat["total_beats"] == 3
    # You cover both, and you're at the venue now.
    assert body["state"]["player"]["credits"] == 200 - 40
    assert body["state"]["player"]["location"] == "the_steeps"

    # First picks each beat: quiet company (3), training talk (2 — but Oona
    # LOVES fitness, so it lands 4), take their hand (3), +4 completion bonus.
    gained_last = None
    for _ in range(3):
        beat = client.post("/api/date/choose", json={"choice_index": 0}).get_json()["date"]
        gained_last = beat
    assert gained_last["done"] is True
    assert gained_last["good"] is True
    assert gained_last["gained"] == 3 + 4 + 3 + 4
    assert "Next time" in gained_last["closing"]
    # The clock billed the whole outing (10:00 + 150m = 12:30).
    _, _, clock = save.load_models()
    assert clock.minute_of_day == 12 * 60 + 30

    cast = {c["id"]: c for c in client.get("/api/characters").get_json()}
    assert cast["oona"]["dated_this_week"] is True


def test_one_outing_a_week_keeps_you_rare(client):
    _warm_up_oona(client)
    for _ in range(2):
        client.post("/api/action", json={"action": "wait"})
    client.post("/api/date/start", json={"npc_id": "oona", "venue": "the_steeps"})
    for _ in range(3):
        client.post("/api/date/choose", json={"choice_index": 0})

    # Back to the Hold — after Oona's 13:00–15:00 tank window — and ask again.
    for _ in range(3):  # 12:30 -> 15:30
        client.post("/api/action", json={"action": "wait"})
    client.post("/api/travel", json={"to": "the_hold", "mode": "walk"})
    res = client.post("/api/date/start", json={"npc_id": "oona", "venue": "the_steeps"})
    assert res.status_code == 400
    assert "Keep me rare" in res.get_json()["error"]

    # Next week the answer changes (re-warm the bond — affection decays).
    save_id, player, clock = save.load_models()
    clock.advance(7 * 24 * 60)
    save.save_models(save_id, player, clock)
    _warm_up_oona(client)
    res = client.post("/api/date/start", json={"npc_id": "oona", "venue": "the_steeps"})
    assert res.status_code == 200


def test_topics_make_the_same_date_play_differently():
    """Oona loves fitness; the training talk lands +2 on top for her."""
    oona = NPC.load("oona")
    scene = dating.scenes()["the_steeps"]
    fitness_choice = next(
        c for beat in scene["beats"] for c in beat["choices"] if c.get("topic") == "fitness"
    )
    from game import preferences

    mod = dating.TOPIC_MODIFIER[preferences.sentiment_of(oona.preferences, "fitness")]
    assert fitness_choice["affection"] + mod == 2 + 2


def test_walking_out_burns_the_week(client):
    _warm_up_oona(client)
    for _ in range(2):
        client.post("/api/action", json={"action": "wait"})
    client.post("/api/date/start", json={"npc_id": "oona", "venue": "the_steeps"})
    res = client.post("/api/date/leave", json={})
    assert res.status_code == 200
    assert "Another time" in res.get_json()["date"]["closing"]
    cast = {c["id"]: c for c in client.get("/api/characters").get_json()}
    assert cast["oona"]["dated_this_week"] is True
    # And you can't be mid-date anymore.
    res = client.post("/api/date/choose", json={"choice_index": 0})
    assert res.status_code == 400


def test_dates_only_happen_where_the_city_dates(client):
    _warm_up_oona(client)
    res = client.post("/api/date/start", json={"npc_id": "oona", "venue": "the_pit"})
    assert res.status_code == 400
    assert "Nobody dates there" in res.get_json()["error"]
    # The market is closed before dusk — the venue's own line answers.
    res = client.post("/api/date/start", json={"npc_id": "oona", "venue": "night_market"})
    assert res.status_code == 400
    assert "18:00" in res.get_json()["error"]
