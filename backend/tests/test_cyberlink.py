"""The Cyberlink — standard-issue neural interface: remote messages to known
contacts (handshake required, one ping per NPC per day, flirting needs warmth
to land), plus the integrated-augment fiction."""

import pytest
from app import create_app
from game import cyberlink, data, save, social
from game.errors import GameError
from game.npc import NPC


def test_every_cast_member_has_a_link_voice():
    voices = data.load("messages")["voices"]
    for cid in NPC.load_all():
        voice = voices.get(cid)
        assert voice, f"{cid} never answers the link"
        for key in ("check_in", "flirt", "joke", "deflect"):
            assert voice.get(key), f"{cid} has no {key} line"


def test_the_cyberlink_is_integrated_standard_issue():
    link = data.load("items")["cyberlink"]
    assert link["slot"] == "integrated"  # below the augment slots — no headroom used
    assert link["value"] == 0
    # Not sold anywhere: everyone already has one.
    for shop_def in data.load("shops").values():
        assert "cyberlink" not in shop_def["stock"]
    # The arrival beat mentions it booting.
    assert "Cyberlink" in data.load("events")["arrival"]["text"]


@pytest.fixture
def client():
    c = create_app().test_client()
    c.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Drifter", "trait": ""},
    )
    return c


def _meet_oona(client):
    """Oona coaches the Hold from 06:00 — walk in and shake three hands."""
    client.post("/api/travel", json={"to": "the_hold", "mode": "walk"})
    start = client.post("/api/dialogue/start", json={"npc_id": "oona"})
    assert start.status_code == 200


def test_messages_need_a_handshake_first(client):
    res = client.post("/api/message", json={"npc_id": "oona", "tone": "check_in"})
    assert res.status_code == 400
    assert "handshake" in res.get_json()["error"]
    _meet_oona(client)
    res = client.post("/api/message", json={"npc_id": "oona", "tone": "check_in"})
    assert res.status_code == 200
    body = res.get_json()["message"]
    assert body["landed"] is True and body["gained"] == 1
    assert "Three arms are spotting" in body["reply"]


def test_one_ping_per_npc_per_day(client):
    _meet_oona(client)
    client.post("/api/message", json={"npc_id": "oona", "tone": "joke"})
    res = client.post("/api/message", json={"npc_id": "oona", "tone": "check_in"})
    assert res.status_code == 400
    assert "Let it breathe" in res.get_json()["error"]
    cast = {c["id"]: c for c in client.get("/api/characters").get_json()}
    assert cast["oona"]["messaged_today"] is True
    assert cast["oona"]["met"] is True
    assert cast["vex"]["met"] is False


def test_flirting_a_stranger_gets_the_deflection(client):
    _meet_oona(client)
    res = client.post("/api/message", json={"npc_id": "oona", "tone": "flirt"}).get_json()
    msg = res["message"]
    assert msg["landed"] is False and msg["gained"] == 0
    assert "new meat" in msg["reply"]  # Oona's own deflection, not a generic


def test_flirting_lands_once_theres_warmth(client):
    _meet_oona(client)
    save_id, player, clock = save.load_models()
    social.add_opinion(save_id, "oona", 15, 1)  # acquaintance
    save.save_models(save_id, player, clock)
    res = client.post("/api/message", json={"npc_id": "oona", "tone": "flirt"}).get_json()
    assert res["message"]["landed"] is True
    assert res["message"]["gained"] == 2


def test_engine_enforces_the_handshake(client):
    _meet_oona(client)
    save_id, player, clock = save.load_models()
    with pytest.raises(GameError, match="handshake"):
        cyberlink.send_message(save_id, player, clock, "vael", "check_in", day=1)


def test_messages_reach_the_unreachable(client):
    """The whole point: ping someone across town, off-shift, at any hour."""
    _meet_oona(client)
    for _ in range(5):  # 08:xx -> 13:xx, Oona's in the tank (do not knock)
        client.post("/api/action", json={"action": "wait"})
    cast = {c["id"]: c for c in client.get("/api/characters").get_json()}
    assert cast["oona"]["reachable"] is False
    res = client.post("/api/message", json={"npc_id": "oona", "tone": "check_in"})
    assert res.status_code == 200
    assert "link sits quiet" in res.get_json()["message"]["reply"]


def test_unknown_npc_and_tone_are_refused(client):
    assert (
        client.post("/api/message", json={"npc_id": "nobody", "tone": "check_in"}).status_code
        == 404
    )
    _meet_oona(client)
    res = client.post("/api/message", json={"npc_id": "oona", "tone": "sonnet"})
    assert res.status_code == 400
