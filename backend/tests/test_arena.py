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
    p.location = "the_pit"
    return p


def _fight_hours():
    """A clock inside the Pit's open hours (first bell at 16:00)."""
    clock = GameClock()
    clock.advance(9 * 60)  # 08:00 -> 17:00
    return clock


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


def test_the_five_titles_then_apex_rematches():
    assert arena.next_bout(_fighter(wins=9))["enemy"]["id"] == "mirrorblade_duessa"
    assert arena.next_bout(_fighter(wins=19))["enemy"]["id"] == "saint_voltage"
    assert arena.next_bout(_fighter(wins=29))["enemy"]["id"] == "gravekeeper_lull"
    assert arena.next_bout(_fighter(wins=39))["enemy"]["id"] == "zenith_crowds_own"
    # Fight #50: the founder steps into their own ring, once.
    assert arena.next_bout(_fighter(wins=49))["enemy"]["id"] == "ondo_the_bell"
    # Beyond the listed titles: every 10th is an Apex rematch.
    assert arena.next_bout(_fighter(wins=59))["enemy"]["id"] == "zenith_crowds_own"


def test_regular_bouts_preview_deterministically():
    a = arena.next_bout(_fighter(wins=3))
    b = arena.next_bout(_fighter(wins=3))
    assert a == b  # the card doesn't reshuffle every time you look at it


def test_losses_dont_advance_the_ladder():
    p = _fighter(wins=9)
    arena.start_fight(p, _fight_hours())
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
    arena.start_fight(p, _fight_hours())
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
    arena.start_fight(p, _fight_hours())
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
    p = _fighter(level=30, wins=59)
    arena.start_fight(p, _fight_hours())
    outcome = _win_current_bout(p)
    champ = outcome["championship"]
    assert champ["title"] == "Apex Rematch"
    assert "prize" not in champ
    assert outcome["cred_gained"] == 20 + 1


# --- Gates ------------------------------------------------------------------------


def test_fights_start_inside_the_venue_during_open_hours():
    p = _fighter()
    p.location = "the_grid"  # standing in the district above isn't enough
    with pytest.raises(GameError, match="step down into the Pit"):
        arena.start_fight(p, _fight_hours())
    p.location = "the_pit"
    with pytest.raises(GameError, match="FIRST BELL AT 16:00"):
        arena.start_fight(p, GameClock())  # 08:00 — the tank is dark
    p.energy = 5
    with pytest.raises(GameError, match="rest first"):
        arena.start_fight(p, _fight_hours())


def test_no_bookings_mid_delve():
    p = _fighter()
    p.dungeon = {"active": True}
    with pytest.raises(GameError, match="mid-delve"):
        arena.start_fight(p, _fight_hours())


def test_championships_cannot_be_fled():
    p = _fighter(level=20, wins=9)
    arena.start_fight(p, _fight_hours())
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


def test_the_founder_out_stats_the_crowds_own():
    # The Founder's Bout is the true apex: Ondo retired undefeated for a reason.
    zenith = combat.scaled_enemy("zenith_crowds_own", 1, "normal")
    ondo = combat.scaled_enemy("ondo_the_bell", 1, "normal")
    for stat in ("hp", "attack", "defense", "speed"):
        assert ondo[stat] > zenith[stat]


def test_champions_never_appear_in_the_dungeon():
    champions = {
        "mirrorblade_duessa",
        "saint_voltage",
        "gravekeeper_lull",
        "zenith_crowds_own",
        "ondo_the_bell",
    }
    for floor in range(1, 11):
        fd = dungeon.generate_floor(77, floor)
        for room in fd["rooms"].values():
            content = room["content"]
            assert content.get("enemy") not in champions
            assert content.get("guard") not in champions


# --- The Founder's Bout -------------------------------------------------------------


def test_founders_bout_pays_cred_and_bell_but_no_purse():
    p = _fighter(level=40, wins=49)
    credits = p.credits
    arena.start_fight(p, _fight_hours())
    assert "steps into their own ring" in p.combat["log"][0]
    outcome = _win_current_bout(p)
    champ = outcome["championship"]
    assert champ["title"] == "The Founder's Bout"
    assert champ["purse"] == 0 and p.credits == credits  # you don't get paid to beat them
    assert champ["prize"] == "Founder's Bell"
    assert p.inventory.get("founders_bell") == 1
    assert outcome["cred_gained"] == 100 + 1


def test_championship_wins_leave_a_defeated_marker():
    p = _fighter(level=40, wins=49)
    arena.start_fight(p, _fight_hours())
    _win_current_bout(p)
    assert "defeated:ondo_the_bell" in p.fired_events
    # Winning again doesn't duplicate the marker.
    p.arena_wins = 49
    arena.start_fight(p, _fight_hours())
    _win_current_bout(p)
    assert p.fired_events.count("defeated:ondo_the_bell") == 1


# --- The book (leaderboard) and the belt rack ---------------------------------------


def test_leaderboard_splices_the_player_in_by_wins():
    rows = arena.leaderboard(_fighter(wins=0))
    you = next(r for r in rows if r.get("you"))
    assert you["name"] == "Kai"
    assert you["rank"] == len(rows)  # zero wins: bottom of the book
    # 100 wins slots between Saint Voltage (121) and Mirrorblade Duessa (77).
    rows = arena.leaderboard(_fighter(wins=100))
    you = next(r for r in rows if r.get("you"))
    assert you["rank"] == 4
    # On a tie the named fighter keeps the higher rank — they got there first.
    rows = arena.leaderboard(_fighter(wins=77))
    duessa = next(r for r in rows if r["name"].startswith("Mirrorblade"))
    you = next(r for r in rows if r.get("you"))
    assert duessa["rank"] == you["rank"] - 1


def test_belt_rack_flips_as_titles_are_taken():
    rack = arena.belts(_fighter(wins=0))
    assert [b["claimed"] for b in rack] == [False] * 5
    rack = arena.belts(_fighter(wins=23))
    assert [b["claimed"] for b in rack] == [True, True, False, False, False]
    assert rack[0]["holder"].startswith("Mirrorblade")
    assert rack[4]["title"] == "The Founder's Bout"


def test_the_bell_line_tracks_your_record():
    assert "New name" in arena._bell_line(_fighter(wins=0))
    assert "on the book" in arena._bell_line(_fighter(wins=4))
    veteran = _fighter(wins=51)
    veteran.fired_events.append("defeated:ondo_the_bell")
    assert "only for you" in arena._bell_line(veteran)


def test_victory_outcomes_carry_a_crowd_line():
    nobody = _fighter()
    arena.start_fight(nobody, _fight_hours())
    outcome = _win_current_bout(nobody)
    assert "barely looks up" in outcome["crowd"]  # Unknown-stage crowd
    somebody = _fighter(wins=30)
    somebody.street_cred = 200
    arena.start_fight(somebody, _fight_hours())
    outcome = _win_current_bout(somebody)
    assert "yours before the bell" in outcome["crowd"]  # Crowd's Own


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
    assert board["venue"] == "the_pit"
    assert board["open"] is False  # 08:00 — first bell is at 16:00
    assert board["wins"] == 0
    assert board["next"]["number"] == 1
    assert board["next"]["championship"] is False
    assert any(r.get("you") for r in board["leaderboard"])
    assert len(board["belts"]) == 5
    assert board["founder"]["record"] == "Undefeated (retired)"

    # The tank is closed in the morning — you can't even climb down.
    resp = client.post("/api/travel", json={"to": "the_pit", "mode": "walk"})
    assert resp.status_code == 400
    assert "FIRST BELL" in resp.get_json()["error"]

    for _ in range(8):  # wait out the day: 08:00 -> 16:00
        client.post("/api/action", json={"action": "wait"})
    client.post("/api/travel", json={"to": "the_grid", "mode": "walk"})
    resp = client.post("/api/travel", json={"to": "the_pit", "mode": "walk"})
    assert resp.status_code == 200
    assert resp.get_json()["state"]["player"]["location"] == "the_pit"
    assert client.get("/api/arena").get_json()["open"] is True

    energy = client.get("/api/game/state").get_json()["player"]["energy"]
    res = client.post("/api/arena/fight")
    assert res.status_code == 200
    body = res.get_json()
    assert body["combat"]["arena"] is True
    assert body["state"]["player"]["energy"] == energy - 10

    # Can't double-book.
    assert client.post("/api/arena/fight").status_code == 400
