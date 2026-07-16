"""The Triumvirate, differentiated (with apologies to Orwell): three corps,
three voices, one loading dock. The war rotates weekly and has always been
this way; records indicating otherwise have been corrected."""

import pytest
from app import create_app
from game import corps, data, encounters, stacks
from game.calendar import GameClock
from game.errors import GameError
from game.player import Player


class FixedRng:
    def __init__(self, value=0.0, pick=0):
        self.value = value
        self.pick = pick

    def random(self):
        return self.value

    def choice(self, seq):
        return seq[self.pick % len(seq)]


# --- Three voices, not one ------------------------------------------------------


def test_each_corp_advertises_in_its_own_voice():
    registry = data.load("corps")
    assert len(registry) == 3
    all_ads = []
    for corp in registry.values():
        assert len(corp["ads"]) >= 4, f"{corp['id']} barely advertises"
        assert corp["denial"], f"{corp['id']} won't even deny Ministry Holdings"
        all_ads.extend(corp["ads"])
    # No line is shared between corps — that was the whole problem.
    assert len(all_ads) == len(set(all_ads))


def test_ads_substitute_and_speak_for_one_corp():
    for pick in range(8):
        ad = encounters._corp_ad(data.load("encounters"), week=2, rng=FixedRng(pick=pick))
        assert ad["type"] == "ad"
        assert ad["corp"] in data.load("corps")
        assert "{" not in ad["text"]  # every placeholder was substituted


# --- The war (we have always been at war) ------------------------------------------


def test_the_war_rotates_and_has_always_been_this_way():
    seen_enemies = set()
    for week in (1, 2, 3):
        war = corps.war_state(week)
        assert len(war["allies"]) == 2
        seen_enemies.add(war["enemy"])
        assert war["line"].endswith("Always.")
        enemy_name = data.load("corps")[war["enemy"]]["name"]
        assert enemy_name in war["bulletin"]
        assert "corrected" in war["bulletin"]
    assert len(seen_enemies) == 3  # everyone gets a turn being eternal
    assert corps.war_state(1) == corps.war_state(4)  # the cycle, eternal too


def test_the_lookout_carries_the_war():
    client = create_app().test_client()
    client.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Drifter", "trait": ""},
    )
    client.post("/api/travel", json={"to": "the_grid", "mode": "walk"})
    client.post("/api/travel", json={"to": "gantry_9", "mode": "walk"})
    board = client.get("/api/lookout").get_json()
    assert board["war"]["line"].endswith("Always.")
    assert "corrected" in board["war"]["bulletin"]


# --- Plant 7 (the file that lists a file) ------------------------------------------


def _at_stacks():
    p = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Drifter", trait="")
    p.location = "the_stacks"
    return p


def test_plant_7_is_a_buried_file_you_read_once():
    p, clock = _at_stacks(), GameClock()
    result = stacks.research(1, p, clock, "plant_7", day=1)
    assert "THE WAR IS THE PRODUCT" in result["text"]
    assert "Ministry Holdings" in result["text"]
    assert "found:plant_7" in p.fired_events

    clock.advance(24 * 60)
    with pytest.raises(GameError, match="maintaining it"):
        stacks.research(1, p, clock, "plant_7", day=2)


def test_the_desk_lists_plant_7_until_read():
    client = create_app().test_client()
    client.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Drifter", "trait": ""},
    )
    client.post("/api/travel", json={"to": "citadel_ring", "mode": "walk"})
    client.post("/api/travel", json={"to": "the_stacks", "mode": "walk"})
    board = client.get("/api/stacks").get_json()
    assert board["plant_7"]["label"] == "Plant 7"

    client.post("/api/research", json={"subject": "plant_7"})
    board = client.get("/api/stacks").get_json()
    assert board["plant_7"] is None  # read what survives; the index moves on
