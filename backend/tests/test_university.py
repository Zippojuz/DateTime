"""The Lyceum & the library's reading rooms: the course ladder (100->400),
one-a-day pacing with 300/400 running as multi-session terms, min-stat and
prerequisite gates, capstone perks that plug into the shared effect system,
readable books, and the collectible Founder's Library quest."""

import pytest
from app import create_app
from game import combat, places, university
from game.calendar import GameClock
from game.errors import GameError
from game.npc import NPC
from game.player import Player


def _player(location="the_lyceum", credits=5000):
    p = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Drifter")
    p.location = location
    p.credits = credits
    return p


def _clock(day=1):
    c = GameClock()
    c.day = day
    return c


# --- The venues --------------------------------------------------------------


def test_the_lyceum_stands_in_the_citadel_ring():
    assert places.district_of("the_lyceum") == "citadel_ring"


def test_library_teaches_the_free_hundreds_only():
    p = _player(location="the_stacks")
    rows = university.catalog(p, _clock())["courses"]
    assert rows, "the reading rooms offer classes"
    assert all(c["tier"] == 100 and c["tuition"] == 0 for c in rows)


def test_lyceum_teaches_the_whole_ladder():
    p = _player()
    tiers = {c["tier"] for c in university.catalog(p, _clock())["courses"]}
    assert tiers == {100, 200, 300, 400}


def test_a_course_isnt_offered_where_it_isnt_taught():
    p = _player(location="docking_quarter")
    with pytest.raises(KeyError):
        # rhet_101 exists, but not on the docks — attend resolves the id then
        # rejects the venue.
        university.attend(p, _clock(), "nope_101", 1)
    assert university.catalog(p, _clock())["courses"] == []


# --- Taking classes ----------------------------------------------------------


def test_a_hundred_grants_points_and_burns_the_day():
    p = _player(location="the_stacks")
    before = p.attributes["charm"]
    res = university.attend(p, _clock(), "rhet_101", 1)
    assert res["completed"]
    assert p.attributes["charm"] == before + 2
    assert "rhet_101" in p.transcript
    # One class a day.
    with pytest.raises(GameError, match="One class a day"):
        university.attend(p, _clock(), "cog_101", 1)


def test_gates_prereq_min_stat_and_tuition():
    p = _player()
    # RHET 301 wants RHET 201 and Charm 12.
    reasons = next(c for c in university.catalog(p, _clock())["courses"] if c["id"] == "rhet_301")
    assert reasons["state"] == "locked"
    with pytest.raises(GameError, match="RHET 201"):
        university.attend(p, _clock(), "rhet_301", 1)
    # Meet the prereq but not the stat.
    p.transcript = ["rhet_101", "rhet_201"]
    with pytest.raises(GameError, match="Charm 12"):
        university.attend(p, _clock(), "rhet_301", 1)
    # Meet both but go broke.
    p.attributes["charm"] = 12
    p.credits = 0
    with pytest.raises(GameError, match="tuition"):
        university.attend(p, _clock(), "rhet_301", 1)


def test_a_seminar_runs_as_a_term_and_grants_its_perk():
    p = _player()
    p.transcript = ["rhet_101", "rhet_201"]
    p.attributes["charm"] = 12
    # Silver Tongue not earned yet.
    assert university.bonus(p, "dialogue_affection_bonus") == 0
    for session in range(1, 4):  # three sessions, one a day
        res = university.attend(p, _clock(day=session), "rhet_301", session)
        if session < 3:
            assert not res["completed"]
            assert res["sessions_done"] == session
    assert "rhet_301" in p.transcript
    assert res["completed"] and res["perk"]["name"] == "Silver Tongue"
    # The perk now resolves through the shared effect vocabulary.
    assert university.bonus(p, "dialogue_affection_bonus") == 1


def test_one_term_at_a_time():
    p = _player()
    p.transcript = ["rhet_101", "rhet_201", "cog_101", "cog_201"]
    p.attributes.update({"charm": 12, "wit": 12})
    university.attend(p, _clock(day=1), "rhet_301", 1)  # start a term
    with pytest.raises(GameError, match="current seminar"):
        university.attend(p, _clock(day=2), "cog_301", 2)


def test_capstone_perk_reaches_combat():
    """Completing The Founder's Nerve (NRV 301) really raises Substrate HP."""
    p = _player()
    base_hp = combat.player_stats(p)["max_hp"]
    p.transcript = ["nrv_301"]
    assert combat.player_stats(p)["max_hp"] > base_hp


# --- Books -------------------------------------------------------------------


def test_reading_a_tome_grants_a_point():
    p = _player()
    p.inventory["primer_lace"] = 1
    before = p.attributes["hacking"]
    res = university.read_book(p, _clock(), "primer_lace")
    assert p.attributes["hacking"] == before + 1
    assert p.inventory.get("primer_lace", 0) == 0  # consumed
    assert res["outcome"]["stat"] == "hacking"


def test_a_tome_can_teach_a_protocol():
    p = _player()
    p.attributes["hacking"] = 8  # Daemoncraft is gated on Hacking 8
    p.inventory["tome_daemon"] = 1
    university.read_book(p, _clock(), "tome_daemon")
    assert "phantom_hands" in p.protocols


def test_a_book_can_be_over_your_head():
    """Level/stat gates: you can hold a book you can't read yet."""
    p = _player()  # fresh: level 1, hacking 5
    p.inventory["masterwork_lace"] = 1  # requires_level 6
    with pytest.raises(GameError, match="over your head"):
        university.read_book(p, _clock(), "masterwork_lace")
    # A stat-gated one, too.
    p.inventory["masterwork_charm"] = 1  # requires charm 10
    with pytest.raises(GameError, match="over your head"):
        university.read_book(p, _clock(), "masterwork_charm")


def test_a_study_guide_rolls_a_random_stat():
    """Randomized training: the stat is rolled from a themed pool (fresh runs).
    A seeded rng makes it deterministic."""
    import random

    p = _player()
    p.inventory["study_guide_mind"] = 1  # pool: wit, hacking, empathy
    res = university.read_book(p, _clock(), "study_guide_mind", rng=random.Random(0))
    assert res["outcome"]["stat"] in ("wit", "hacking", "empathy")
    assert p.inventory.get("study_guide_mind", 0) == 0  # consumed


def test_lore_books_are_keepers_that_file_a_flag():
    p = _player()
    p.inventory["lore_founding"] = 1
    res = university.read_book(p, _clock(), "lore_founding")
    assert res["lore"]["title"] == "The Founding of Nexus City"
    assert res["first_time"] is True
    assert "lore:founding" in p.fired_events
    assert p.inventory.get("lore_founding", 0) == 1  # NOT consumed — it's a keeper
    # Reading again is fine but no longer "first time".
    assert university.read_book(p, _clock(), "lore_founding")["first_time"] is False


def test_reading_the_prospectus_reveals_lore_without_spending_it():
    """The quest book is readable for its lore, and stays in the pack — so it
    still satisfies SYS 401's requires_book gate."""
    p = _player()
    p.inventory["ministry_prospectus"] = 1
    res = university.read_book(p, _clock(), "ministry_prospectus")
    assert "war is the product" in res["lore"]["text"].lower()
    assert p.inventory.get("ministry_prospectus", 0) == 1


# --- Browsing the shelves ----------------------------------------------------


def test_browsing_turns_up_a_library_book_once_a_day():
    import random

    p = _player(location="the_stacks")
    res = university.browse_shelves(p, _clock(), 1, rng=random.Random(1))
    assert res["found"] is not None
    found_id = res["found"]["id"]
    assert found_id in p.inventory
    # It's a library-sourced book, never a dungeon-exclusive one.
    assert university.books()[found_id]["source"] in ("library", "both")
    # One browse a day.
    with pytest.raises(GameError, match="afternoon in the stacks"):
        university.browse_shelves(p, _clock(), 1)


def test_dungeon_exclusive_books_never_appear_on_the_shelves():
    import random

    p = _player(location="the_stacks")
    seen = set()
    day = 0
    for _ in range(40):
        day += 1
        p.browse_day = 0  # reset the daily gate for the sweep
        res = university.browse_shelves(p, _clock(day=day), day, rng=random.Random(day))
        if res["found"]:
            seen.add(res["found"]["id"])
    assert "tome_nerve" not in seen  # dungeon-exclusive
    assert "ministry_prospectus" not in seen  # quest-only


# --- The Founder's Library quest ---------------------------------------------


def test_the_collectible_set_unlocks_the_founders_seminar():
    p = _player()
    fnd = next(c for c in university.catalog(p, _clock())["courses"] if c["id"] == "fnd_401")
    assert fnd["state"] == "locked"  # needs the quest done

    for i in range(1, 5):
        p.inventory[f"folio_founders_{i}"] = 1
    board = {q["id"]: q for q in university.catalog(p, _clock())["quests"]}
    assert board["founders_library"]["state"] == "ready"

    res = university.turn_in(p, _clock(), "founders_library")
    assert res["unlocks"] == "fnd_401"
    assert res["reward_credits"] == 200
    # Volumes are consumed; the flag is set.
    assert all(p.inventory.get(f"folio_founders_{i}", 0) == 0 for i in range(1, 5))
    fnd = next(c for c in university.catalog(p, _clock())["courses"] if c["id"] == "fnd_401")
    assert fnd["state"] == "available"


def test_turn_in_happens_at_the_lyceum():
    p = _player(location="the_stacks")
    for i in range(1, 5):
        p.inventory[f"folio_founders_{i}"] = 1
    with pytest.raises(GameError, match="Lyceum"):
        university.turn_in(p, _clock(), "founders_library")


def test_sys_401_is_gated_by_a_book_from_the_deep():
    p = _player()
    p.transcript = ["sys_101", "sys_201", "sys_301"]
    p.attributes["hacking"] = 15
    row = next(c for c in university.catalog(p, _clock())["courses"] if c["id"] == "sys_401")
    assert row["state"] == "locked"
    assert any("Prospectus" in r for r in row["reasons"])
    p.inventory["ministry_prospectus"] = 1
    row = next(c for c in university.catalog(p, _clock())["courses"] if c["id"] == "sys_401")
    assert row["state"] == "available"


# --- The professor -----------------------------------------------------------


def test_the_professor_is_cast_and_romanceable():
    ines = NPC.load("ines")
    assert ines.romanceable
    assert not ines.requires_perception


# --- API ---------------------------------------------------------------------


def test_lyceum_route_serves_the_catalog():
    client = create_app().test_client()
    client.post("/api/game/new", json={"name": "Kai", "pronouns": "they/them"})
    res = client.get("/api/lyceum")
    assert res.status_code == 200
    body = res.get_json()
    # Fresh on the docks: nothing offered here, but the shape is right.
    assert body["courses"] == [] and body["quests"]
