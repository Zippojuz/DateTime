"""Districts, travel, and NPC availability. (Milestone 2 / 3)

The city is a ring of five districts. Travel between them costs time and energy
(and credits for fast transit); adjacent hops are cheaper than cross-city. NPC
availability is resolved from schedules, and — as of Milestone 3 — you must be
in the same district as an NPC to reach them.
"""

from game import data
from game.errors import GameError

# Travel cost by (distance, mode): distance is "adjacent" or "cross".
TRAVEL_COST = {
    ("adjacent", "walk"): {"minutes": 20, "energy": -8, "credits": 0},
    ("adjacent", "transit"): {"minutes": 8, "energy": -3, "credits": 8},
    ("cross", "walk"): {"minutes": 40, "energy": -15, "credits": 0},
    ("cross", "transit"): {"minutes": 18, "energy": -6, "credits": 18},
}


def districts():
    return data.load("districts")


def are_adjacent(a, b):
    d = districts()
    return b in d.get(a, {}).get("adjacent", [])


def travel_cost(from_id, to_id, mode):
    distance = "adjacent" if are_adjacent(from_id, to_id) else "cross"
    cost = TRAVEL_COST.get((distance, mode))
    if cost is None:
        raise GameError(f"Unknown travel mode: {mode!r}")
    return {"distance": distance, **cost}


def travel(player, clock, to_id, mode):
    """Move the player to another district in place. Raises GameError on invalid
    destinations, insufficient credits, or exhaustion. Returns the cost applied."""
    if to_id not in districts():
        raise GameError("There's no such district.")
    if to_id == player.location:
        raise GameError("You're already there.")

    cost = travel_cost(player.location, to_id, mode)
    if player.credits < cost["credits"]:
        raise GameError("Not enough credits for transit.")
    if player.energy + cost["energy"] < 0:
        raise GameError("Too tired to travel — rest first.")

    player.credits -= cost["credits"]
    player.energy = max(0, player.energy + cost["energy"])
    player.location = to_id
    clock.advance(cost["minutes"])
    return cost


# Arriving-late tiers, by minutes remaining in the current availability window.
TIER_FULL = "full"
TIER_SHORTENED = "shortened"
TIER_BRIEF = "brief"
TIER_MISSED = "missed"
TIER_UNAVAILABLE = "unavailable"

# Affection multiplier per tier (design doc -> "Arriving Late"). Shortened and
# brief scenes yield less; a just-missed glimpse yields nothing.
TIER_MULTIPLIER = {
    TIER_FULL: 1.0,
    TIER_SHORTENED: 0.6,
    TIER_BRIEF: 0.3,
    TIER_MISSED: 0.0,
    TIER_UNAVAILABLE: 0.0,
}

DAY_MINUTES = 24 * 60


def _to_minutes(hhmm):
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def _in_window(minute, start, end):
    """True if `minute` is within [start, end), handling midnight wrap."""
    if start <= end:
        return start <= minute < end
    return minute >= start or minute < end  # window crosses midnight


def _minutes_left(minute, end):
    diff = end - minute
    if diff <= 0:
        diff += DAY_MINUTES
    return diff


def _tier(minutes_left):
    if minutes_left >= 60:
        return TIER_FULL
    if minutes_left >= 30:
        return TIER_SHORTENED
    if minutes_left >= 10:
        return TIER_BRIEF
    return TIER_MISSED


def availability(npc, clock):
    """Resolve an NPC's availability at the current time.

    Returns {available, tier, location, minutes_left}. `available` is True only
    for full/shortened/brief tiers — a just-missed glimpse or an off-duty window
    can't be talked to.
    """
    now = clock.minute_of_day
    for window in npc.schedule:
        start = _to_minutes(window["start"])
        end = _to_minutes(window["end"])
        if not _in_window(now, start, end):
            continue
        district = window.get("district")
        if not window.get("available", True):
            return {
                "available": False,
                "tier": TIER_UNAVAILABLE,
                "location": window.get("location"),
                "district": district,
                "minutes_left": 0,
            }
        left = _minutes_left(now, end)
        tier = _tier(left)
        return {
            "available": tier != TIER_MISSED,
            "tier": tier,
            "location": window.get("location"),
            "district": district,
            "minutes_left": left,
        }
    return {
        "available": False,
        "tier": TIER_UNAVAILABLE,
        "location": None,
        "district": None,
        "minutes_left": 0,
    }
