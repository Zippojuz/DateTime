"""Milestone 3: districts, travel, credits, co-location, encounters."""

import random

import pytest
from app import create_app
from game import encounters, world
from game.npc import NPC


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    return c


# --- Starting state ---------------------------------------------------------


def test_player_starts_in_docking_quarter_with_credits(client):
    player = client.get("/api/game/state").get_json()["player"]
    assert player["location"] == "docking_quarter"
    assert player["credits"] == 50


# --- Districts & adjacency --------------------------------------------------


def test_all_five_districts_present(client):
    districts = client.get("/api/districts").get_json()
    assert set(districts) == {
        "docking_quarter",
        "the_grid",
        "citadel_ring",
        "bloom_district",
        "the_shallows",
    }


def test_adjacency_is_symmetric():
    d = world.districts()
    for did, entry in d.items():
        for neighbour in entry["adjacent"]:
            assert did in d[neighbour]["adjacent"], f"{did}<->{neighbour} not symmetric"


def test_travel_cost_tiers():
    # docking_quarter <-> the_grid are adjacent; citadel_ring is cross-city.
    assert world.travel_cost("docking_quarter", "the_grid", "walk")["distance"] == "adjacent"
    assert world.travel_cost("docking_quarter", "citadel_ring", "walk")["distance"] == "cross"


# --- Travel via the API -----------------------------------------------------


def test_walk_costs_time_and_energy_but_no_credits(client):
    res = client.post("/api/travel", json={"to": "the_grid", "mode": "walk"}).get_json()
    player = res["state"]["player"]
    assert player["location"] == "the_grid"
    assert player["credits"] == 50  # walking is free
    assert player["energy"] == 92  # -8 adjacent walk
    assert res["state"]["clock"]["time"] == "08:20"  # +20 min


def _untraited(client):
    """A fresh save with a free-text species — no trait, so transit isn't
    free (the default human's Priced In trait rides at no charge)."""
    client.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her", "species": "Drifter"})


def test_transit_costs_credits(client):
    _untraited(client)
    res = client.post("/api/travel", json={"to": "the_grid", "mode": "transit"}).get_json()
    player = res["state"]["player"]
    assert player["credits"] == 42  # 50 - 8
    assert res["state"]["clock"]["time"] == "08:08"


def test_transit_is_free_for_the_priced_in(client):
    # The default human carries Priced In: the city was built for them.
    res = client.post("/api/travel", json={"to": "the_grid", "mode": "transit"}).get_json()
    assert res["state"]["player"]["credits"] == 50


def test_cross_city_is_more_expensive(client):
    _untraited(client)
    res = client.post("/api/travel", json={"to": "citadel_ring", "mode": "transit"}).get_json()
    player = res["state"]["player"]
    assert player["credits"] == 32  # 50 - 18
    assert player["location"] == "citadel_ring"


def test_cannot_travel_without_enough_credits(client):
    _untraited(client)
    # Loop the ring by transit — each adjacent hop is 8 credits: 50 -> 10.
    for dest in ("the_grid", "citadel_ring", "bloom_district", "the_shallows", "docking_quarter"):
        client.post("/api/travel", json={"to": dest, "mode": "transit"})
    # 10 credits left; a cross-city transit (18) is unaffordable.
    resp = client.post("/api/travel", json={"to": "citadel_ring", "mode": "transit"})
    assert resp.status_code == 400
    assert "credits" in resp.get_json()["error"].lower()


def test_cannot_travel_to_current_or_unknown(client):
    assert client.post("/api/travel", json={"to": "docking_quarter"}).status_code == 400
    assert client.post("/api/travel", json={"to": "atlantis"}).status_code == 400


# --- Co-location gating -----------------------------------------------------


def test_cannot_talk_across_districts(client):
    # Carro is in the Docking Quarter (where we start) — but reach depends on
    # time. Vael is in the Citadel Ring; talking to her from here is blocked.
    for _ in range(9):  # advance to ~17:00 so Vael is on-shift at the plaza
        client.post("/api/action", json={"action": "wait"})
    resp = client.post("/api/dialogue/start", json={"npc_id": "vael"})
    assert resp.status_code == 400
    assert "citadel" in resp.get_json()["error"].lower()


def test_characters_report_reachability(client):
    chars = {c["id"]: c for c in client.get("/api/characters").get_json()}
    # At 08:00 in the Docking Quarter, Vael (Citadel Ring) is not reachable.
    assert chars["vael"]["reachable"] is False
    assert chars["vael"]["district"] == "citadel_ring"


# --- New characters ---------------------------------------------------------


def test_all_five_characters_load_with_schedules_and_prefs():
    npcs = NPC.load_all()
    # The base cast, Nyx (locked behind her floor-10 fight), the fixer, the
    # doc, the pit master, and the coach.
    assert set(npcs) == {
        "vael",
        "zix",
        "sora",
        "carro",
        "miko",
        "nyx",
        "vex",
        "juno",
        "ondo",
        "oona",
    }
    assert npcs["nyx"].requires_defeat == "nyx_deep_signal"
    for npc in npcs.values():
        assert npc.schedule, f"{npc.id} has no schedule"
        assert all("district" in w for w in npc.schedule)
        assert npc.preferences, f"{npc.id} has no preferences"


def test_each_character_has_an_intro_dialogue():
    from game import dialogue

    for npc_id in ("vael", "zix", "sora", "carro", "miko"):
        assert dialogue.tree_for_npc(npc_id) is not None


# --- Encounters -------------------------------------------------------------


def test_encounter_none_when_roll_high():
    rng = random.Random()
    rng.random = lambda: 0.99  # above ENCOUNTER_CHANCE
    assert encounters.roll_encounter({}, set(), rng=rng) is None


def test_sighting_only_for_met_npcs():
    # Force an encounter and steer it to a sighting.
    class Rng:
        def random(self):
            return 0.0

        def choice(self, seq):
            # pick 'sighting' from kinds, then the npc, then the line
            if "sighting" in seq:
                return "sighting"
            return seq[0]

    enc = encounters.roll_encounter({"vael": "Vael"}, {"vael"}, rng=Rng())
    assert enc["type"] == "sighting"
    assert enc["npc_id"] == "vael"
    assert enc["affection"] == encounters.SIGHTING_AFFECTION
    assert "Vael" in enc["text"]
