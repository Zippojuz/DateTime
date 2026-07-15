"""The Pit: the arena win ladder, championships, and street cred (arena +
dungeon depth records)."""

import pytest
from app import create_app
from game import arena, combat, dungeon
from game.calendar import GameClock
from game.errors import GameError
from game.player import Player


class QuietRng:
    def uniform(self, a, b):
        return 1.0

    def random(self):
        return 0.99

    def choice(self, seq):
        return seq[0]

    def randint(self, a, b):
        return b


def _fighter(level=10, wins=0):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.combat_level = level
    p.arena_wins = wins
    p.location = "docking_quarter"
    return p


def _win_current_bout(p):
    """Force-resolve the active bout as a victory and settle it."""
    p.combat["over"] = True
    p.combat["victory"] = True
    p.combat["fled"] = False
    return arena.finish_fight(p)


# --- The ladder --------------------------------------------------------------------


def test_every_tenth_fight_is_a_championship():
    for wins, championship in ((0, False), (8, False), (9, True), (19, True), (39, True)):
        bout = arena.next_bout(_fighter(wins=wins))
        assert bout["number"] == wins + 1
        assert bout["championship"] is championship


def test_the_four_titles_then_apex_rematches():
    assert arena.next_bout(_fighter(wins=9))["enemy"]["id"] == "mirrorblade_duessa"
    assert arena.next_bout(_fighter(wins=19))["enemy"]["id"] == "saint_voltage"
    assert arena.next_bout(_fighter(wins=29))["enemy"]["id"] == "gravekeeper_lull"
    assert arena.next_bout(_fighter(wins=39))["enemy"]["id"] == "zenith_crowds_own"
    # Beyond the listed titles: every 10th is an Apex rematch.
    assert arena.next_bout(_fighter(wins=49))["enemy"]["id"] == "zenith_crowds_own"


def test_regular_bouts_preview_deterministically():
    a = arena.next_bout(_fighter(wins=3))
    b = arena.next_bout(_fighter(wins=3))
    assert a == b  # the card doesn't reshuffle every time you look at it


def test_losses_dont_advance_the_ladder():
    p = _fighter(wins=9)
    arena.start_fight(p, GameClock())
    p.combat.update(over=True, victory=False, fled=False)
    outcome = arena.finish_fight(p)
    assert outcome["result"] == "defeat"
    assert p.arena_wins == 9
    # The championship is still waiting right where you left it.
    assert arena.next_bout(p)["championship"] is True


# --- No spoils in the Pit -------------------------------------------------------------


def test_arena_wins_grant_no_xp_credits_or_drops():
    p = _fighter()
    xp, credits, level = p.combat_xp, p.credits, p.combat_level
    inv = dict(p.inventory)
    arena.start_fight(p, GameClock())
    p.combat["enemy_hp"] = 1
    combat.act(p, p.combat, "attack", rng=QuietRng())
    assert p.combat["victory"] is True
    assert p.combat["rewards"] is None
    assert (p.combat_xp, p.credits - 0, p.combat_level) == (xp, credits, level)
    outcome = arena.finish_fight(p)
    assert outcome["result"] == "victory"
    assert p.inventory == inv  # nothing dropped
    assert p.credits == credits  # regular win: no purse either
    assert p.street_cred == 1  # ...but the Pit pays in reputation
    assert p.arena_wins == 1


def test_championship_pays_title_purse_prize_and_cred():
    p = _fighter(level=20, wins=9)
    credits = p.credits
    arena.start_fight(p, GameClock())
    assert "CHAMPIONSHIP" in p.combat["log"][0]
    outcome = _win_current_bout(p)
    champ = outcome["championship"]
    assert champ["title"] == "Gatekeeper's Bout"
    assert champ["purse"] == 100 and p.credits == credits + 100
    assert champ["prize"] == "Pit Champion's Belt"
    assert p.inventory.get("pit_champions_belt") == 1
    assert outcome["cred_gained"] == 15 + 1  # title cred + the win itself
    assert p.arena_wins == 10


def test_apex_rematch_pays_cred_and_purse_but_no_prize():
    p = _fighter(level=30, wins=49)
    arena.start_fight(p, GameClock())
    outcome = _win_current_bout(p)
    champ = outcome["championship"]
    assert champ["title"] == "Apex Rematch"
    assert "prize" not in champ
    assert outcome["cred_gained"] == 20 + 1


# --- Gates ------------------------------------------------------------------------


def test_the_pit_is_docks_only_and_costs_energy():
    p = _fighter()
    p.location = "the_grid"
    with pytest.raises(GameError, match="Docking Quarter"):
        arena.start_fight(p, GameClock())
    p.location = "docking_quarter"
    p.energy = 5
    with pytest.raises(GameError, match="rest first"):
        arena.start_fight(p, GameClock())


def test_no_bookings_mid_delve():
    p = _fighter()
    p.dungeon = {"active": True}
    with pytest.raises(GameError, match="mid-delve"):
        arena.start_fight(p, GameClock())


def test_championships_cannot_be_fled():
    p = _fighter(level=20, wins=9)
    arena.start_fight(p, GameClock())
    with pytest.raises(GameError, match="won't let you leave"):
        combat.act(p, p.combat, "flee", rng=QuietRng())


# --- The champions are the top of the food chain ---------------------------------------


def test_zenith_out_stats_the_hardest_dungeon_boss():
    # Nyx (floor 10) is the hardest thing under the city; Zenith fights at
    # tuned base stats (arena floor scale 1.0) and must still beat Nyx's
    # floor-scaled numbers.
    nyx = combat.scaled_enemy("nyx_deep_signal", 10, "normal")
    zenith = combat.scaled_enemy("zenith_crowds_own", 1, "normal")
    lull = combat.scaled_enemy("gravekeeper_lull", 1, "normal")
    assert zenith["hp"] > nyx["hp"]
    assert zenith["attack"] > nyx["attack"]
    assert zenith["defense"] > nyx["defense"]
    assert lull["hp"] > nyx["hp"]  # the third champion already edges her out


def test_champions_never_appear_in_the_dungeon():
    champions = {"mirrorblade_duessa", "saint_voltage", "gravekeeper_lull", "zenith_crowds_own"}
    for floor in range(1, 11):
        fd = dungeon.generate_floor(77, floor)
        for room in fd["rooms"].values():
            content = room["content"]
            assert content.get("enemy") not in champions
            assert content.get("guard") not in champions


# --- Street cred from depth records ------------------------------------------------


def test_new_depth_records_pay_cred_once():
    p = _fighter()
    p.location = dungeon.ENTRANCE_DISTRICT
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    assert p.street_cred == 2  # floor 1 record: 2 x 1
    result = dungeon.descend(p, clock)
    assert p.street_cred == 2 + 4  # floor 2 record: 2 x 2
    assert result["cred_gained"] == 4
    assert "+4 cred" in result["text"]
    # Leaving and re-descending to a known floor pays nothing.
    dungeon.leave(p, clock)
    dungeon.enter(p, clock, seed=8)
    result = dungeon.descend(p, clock)
    assert result["cred_gained"] == 0
    assert p.street_cred == 6


# --- Cred stages -------------------------------------------------------------------


def test_cred_stages_scale():
    assert arena.cred_stage(0) == "Unknown"
    assert arena.cred_stage(12) == "Known Face"
    assert arena.cred_stage(55) == "Name in the Grid"
    assert arena.cred_stage(150) == "Undercard Legend"
    assert arena.cred_stage(500) == "Crowd's Own"


# --- API --------------------------------------------------------------------------


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    return c


def test_arena_api_flow(client):
    board = client.get("/api/arena").get_json()
    assert board["name"] == "The Pit"
    assert board["wins"] == 0
    assert board["next"]["number"] == 1
    assert board["next"]["championship"] is False

    res = client.post("/api/arena/fight")
    assert res.status_code == 200
    body = res.get_json()
    assert body["combat"]["arena"] is True
    assert body["state"]["player"]["energy"] == 90

    # Can't double-book.
    assert client.post("/api/arena/fight").status_code == 400
