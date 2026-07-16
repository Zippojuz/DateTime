"""The Stacks — the Citadel Ring's archive: wit/hacking house rates, the
research desk (one pull a day, files on people you've met), and Index — the
ghost archivist, present from day one but imperceivable until you learn how
to look (or were born hearing it)."""

import pytest
from app import create_app
from game import actions, places, stacks
from game.calendar import GameClock
from game.errors import GameError
from game.npc import NPC, perceives_unseen
from game.player import Player


def _player(location="the_stacks", trait=""):
    p = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Drifter", trait=trait)
    p.location = location
    return p


# --- The venue ---------------------------------------------------------------


def test_the_archive_never_closes():
    assert places.district_of("the_stacks") == "citadel_ring"
    assert places.is_open("the_stacks", GameClock())
    late = GameClock()
    late.advance(19 * 60)  # 03:00
    assert places.is_open("the_stacks", late)


def test_reading_rooms_coach_wit_and_hacking():
    p = _player()
    assert actions.house_rates(p, "wit")["minutes"] == 60
    assert actions.house_rates(p, "hacking")["energy"] == -8
    assert actions.house_rates(p, "courage") is None  # that's the Hold's job


# --- Perceiving Index --------------------------------------------------------


def test_index_is_imperceivable_until_you_learn_to_look():
    p = _player()
    assert not perceives_unseen(p)
    assert "index" not in NPC.load_unlocked(p)
    p.inventory["archivists_lens"] = 1
    assert perceives_unseen(p)
    assert "index" in NPC.load_unlocked(p)


def test_substrate_born_hear_them_from_day_one():
    native = _player(trait="substrate_born")
    assert perceives_unseen(native)
    assert "index" in NPC.load_unlocked(native)


def test_researching_the_draft_grants_the_lens_once():
    p, clock = _player(), GameClock()
    result = stacks.research(1, p, clock, "the_draft", day=1)
    assert result["unlocked"] == "index"
    assert p.inventory["archivists_lens"] == 1
    assert "found:archivists_lens" in p.fired_events
    assert clock.minute_of_day == 8 * 60 + 90

    clock.advance(24 * 60)  # a fresh pull tomorrow —
    with pytest.raises(GameError, match="They know you know"):
        stacks.research(1, p, clock, "the_draft", day=2)


def test_natives_cant_farm_the_draft():
    native = _player(trait="substrate_born")
    with pytest.raises(GameError, match="already know"):
        stacks.research(1, native, GameClock(), "the_draft", day=1)


# --- The research desk (rules) -------------------------------------------------


def test_the_desk_stays_in_the_stacks_and_closes_after_one_pull():
    away = _player(location="citadel_ring")
    with pytest.raises(GameError, match="files don't check out"):
        stacks.research(1, away, GameClock(), "the_draft", day=1)

    p, clock = _player(), GameClock()
    stacks.research(1, p, clock, "the_draft", day=1)
    with pytest.raises(GameError, match="One pull a day"):
        stacks.research(1, p, clock, "vael", day=1)


def test_the_archive_has_no_file_on_strangers_or_ghosts():
    p = _player()
    with pytest.raises(KeyError):
        stacks.research(1, p, GameClock(), "nobody", day=1)
    # Index is filed under 'draft' until perceived — asking by name leaks nothing.
    with pytest.raises(KeyError):
        stacks.research(1, p, GameClock(), "index", day=1)


# --- Over the API --------------------------------------------------------------


@pytest.fixture
def client():
    c = create_app().test_client()
    c.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Drifter", "trait": ""},
    )
    return c


def _to_stacks(client):
    client.post("/api/travel", json={"to": "citadel_ring", "mode": "walk"})
    client.post("/api/travel", json={"to": "the_stacks", "mode": "walk"})


def test_pulling_a_file_reveals_a_marked_preference(client):
    # Meet Oona first (the archive files people under who they are to you).
    client.post("/api/travel", json={"to": "the_hold", "mode": "walk"})
    client.post("/api/dialogue/start", json={"npc_id": "oona"})
    _to_stacks(client)

    res = client.post("/api/research", json={"subject": "vex"})
    assert res.status_code == 400  # never actually met Vex
    assert "meet them in person" in res.get_json()["error"]

    res = client.post("/api/research", json={"subject": "oona"})
    assert res.status_code == 200
    pulled = res.get_json()["research"]
    assert pulled["npc"].startswith("Oona") and pulled["topic"] and pulled["sentiment"]
    # Unlike gossip, a file is a source: the discovery is marked.
    cast = {c["id"]: c for c in client.get("/api/characters").get_json()}
    assert pulled["topic"] in cast["oona"]["preferences"]


def test_the_draft_unlocks_index_end_to_end(client):
    cast = {c["id"] for c in client.get("/api/characters").get_json()}
    assert "index" not in cast

    _to_stacks(client)
    res = client.post("/api/research", json={"subject": "the_draft"})
    assert res.status_code == 200
    assert "reading over your shoulder" in res.get_json()["research"]["text"]

    cast = {c["id"]: c for c in client.get("/api/characters").get_json()}
    assert "index" in cast
    assert cast["index"]["reachable"] is True  # they're... here. Everywhere.
    start = client.post("/api/dialogue/start", json={"npc_id": "index"})
    assert start.status_code == 200
    assert "Row nine" in start.get_json()["node"]["text"]

    # The desk knows the draft is found: it stops offering it.
    board = client.get("/api/stacks").get_json()
    assert board["draft"] is None and board["researched_today"] is True
