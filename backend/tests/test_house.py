"""A place to live: the housing ladder (rent-then-buy), home-only full rest with
a berth fallback, weekly rent settlement and eviction, per-home perks that plug
into the shared effect system, the item stash, and private-door travel gating."""

import pytest
from game import actions, combat, house, places, world
from game.calendar import GameClock
from game.errors import GameError
from game.player import Player


def _player(location="docking_quarter", credits=5000):
    p = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Drifter")
    p.location = location
    p.credits = credits
    return p


def _clock(week=1):
    c = GameClock()
    c.week = week
    return c


# --- Homes are places --------------------------------------------------------


def test_berth_is_the_free_starting_home():
    p = _player()
    assert p.home == "berth"
    assert house.current(p)["rent"] == 0
    assert house.current(p)["price"] == 0


def test_homes_resolve_as_travellable_places():
    assert places.get("tide_houseboat")["name"]
    assert places.district_of("tide_houseboat") == "docking_quarter"
    assert places.district_of("citadel_arcology") == "citadel_ring"


# --- Renting -----------------------------------------------------------------


def test_rent_moves_you_in_and_charges_the_first_week():
    p = _player(credits=100)
    result = house.rent(p, _clock(week=3), "capsule_stack")
    assert result["moved_in"] and result["paid"] == 25
    assert p.home == "capsule_stack"
    assert p.credits == 75
    assert p.rent_paid_week == 3


def test_rent_needs_the_credits():
    p = _player(credits=10)
    with pytest.raises(GameError):
        house.rent(p, _clock(), "capsule_stack")


def test_cannot_rent_the_berth():
    with pytest.raises(GameError):
        house.rent(_player(), _clock(), "berth")


# --- Buying ------------------------------------------------------------------


def test_buy_owns_it_forever_with_no_drain():
    p = _player(credits=2000)
    result = house.buy(p, _clock(week=5), "tide_houseboat")
    assert result["owned"] and result["paid"] == 1100
    assert "tide_houseboat" in p.owned_homes
    assert p.home == "tide_houseboat"
    assert p.rent_paid_week == 0  # owned: never charged rent
    # A later week owes nothing.
    assert house.settle_rent(p, _clock(week=40)) is None


def test_buy_needs_the_lump_sum():
    with pytest.raises(GameError):
        house.buy(_player(credits=100), _clock(), "tide_houseboat")


# --- Rent settlement & eviction ---------------------------------------------


def test_rent_drains_weekly():
    p = _player(credits=200)
    house.rent(p, _clock(week=1), "capsule_stack")  # -25 -> 175, paid through wk1
    event = house.settle_rent(p, _clock(week=4))  # owes weeks 2,3,4 = 3 * 25
    assert event["paid"] == 75 and not event["evicted"]
    assert p.credits == 100
    assert p.rent_paid_week == 4


def test_missed_rent_evicts_to_the_berth():
    p = _player(credits=60)
    house.rent(p, _clock(week=1), "tide_houseboat")  # -55 -> 5, paid wk1
    p.location = "tide_houseboat"
    event = house.settle_rent(p, _clock(week=2))  # owes 55, only has 5
    assert event["evicted"]
    assert p.home == "berth"
    assert p.credits == 5  # nothing charged on eviction
    assert p.location == "docking_quarter"  # tipped back out of the unit


# --- Rest is home-only -------------------------------------------------------


def test_full_rest_requires_being_home():
    p = _player(location="the_grid")  # out in the city
    with pytest.raises(GameError):
        actions.apply_action(p, GameClock(), "rest")


def test_rest_at_home_restores_and_uses_home_rest_time():
    p = _player(location="berth")
    p.energy = 20
    _, clock = actions.apply_action(p, GameClock(), "rest")
    assert p.energy == 100
    assert clock.minute_of_day == 8 * 60 + 540  # berth's slow 9h sleep


def test_a_nicer_home_rests_faster():
    p = _player(credits=5000)
    house.buy(p, _clock(), "citadel_arcology")
    p.location = "citadel_arcology"
    p.energy = 0
    _, clock = actions.apply_action(p, GameClock(), "rest")
    assert clock.minute_of_day == 8 * 60 + 360  # arcology's 6h


def test_catnap_works_anywhere():
    p = _player(location="the_grid")
    p.energy = 10
    actions.apply_action(p, GameClock(), "nap")  # no raise
    assert p.energy == 40


# --- Perks plug into the shared effect system --------------------------------


def test_home_perk_feeds_the_effect_vocabulary():
    p = _player(credits=2000)
    base = combat.player_stats(p)["luck"]
    house.buy(p, _clock(), "tide_houseboat")  # perk: luck_bonus +1
    assert combat.player_stats(p)["luck"] == base + 1


def test_you_only_get_the_perk_of_where_you_live():
    p = _player(credits=7000)
    house.buy(p, _clock(), "tide_houseboat")  # luck +1
    house.buy(p, _clock(), "citadel_arcology")  # move in here (no luck perk)
    assert combat.player_stats(p)["luck"] == p.attributes["luck"]  # berth-equal


# --- Stash -------------------------------------------------------------------


def test_stash_holds_items_at_home_within_capacity():
    p = _player(credits=2000)
    house.buy(p, _clock(), "capsule_stack")
    p.location = "capsule_stack"
    p.inventory = {"protein_cube": 3}
    house.stash_deposit(p, "protein_cube", 2)
    assert p.stash["protein_cube"] == 2
    assert p.inventory["protein_cube"] == 1
    house.stash_withdraw(p, "protein_cube", 1)
    assert p.inventory["protein_cube"] == 2


def test_stash_needs_you_home():
    p = _player(credits=2000)
    house.buy(p, _clock(), "capsule_stack")  # home is now the capsule...
    p.location = "the_grid"  # ...but you're out
    p.inventory = {"protein_cube": 1}
    with pytest.raises(GameError):
        house.stash_deposit(p, "protein_cube", 1)


# --- Travel gating -----------------------------------------------------------


def test_cannot_walk_into_a_home_that_isnt_yours():
    p = _player(location="citadel_ring")
    with pytest.raises(GameError):
        world.travel(p, GameClock(), "citadel_arcology", "walk")


def test_can_travel_to_your_own_home():
    p = _player(location="docking_quarter")  # berth's district
    world.travel(p, GameClock(), "berth", "walk")  # no raise (local hop)
    assert p.location == "berth"
