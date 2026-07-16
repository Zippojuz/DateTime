"""Districts, travel, and NPC availability. (Milestone 2 / 3)

The city is a ring of five districts, plus venues nested inside them (see
game/places.py). Three ways to move:
- walk: free, slow (Rooftop Lines halves it)
- transit — the Loop, a pneumatic mag-tube ring: cheap, station to station,
  adjacent hops cheaper than cross-city (free for the Priced In)
- cab — hovercab sky lanes: door to door, any place to any place including
  straight to a venue, flat rate, never free for anyone

Stepping into or out of a venue within the same district is a short local
hop. NPC availability is resolved from schedules, and — as of Milestone 3 —
you must be in the same place as an NPC to reach them.
"""

from game import data, places, teahouse, traits
from game.errors import GameError

# Travel cost by (distance, mode): distance is "adjacent" or "cross".
TRAVEL_COST = {
    ("adjacent", "walk"): {"minutes": 20, "energy": -8, "credits": 0},
    ("adjacent", "transit"): {"minutes": 8, "energy": -3, "credits": 8},
    ("cross", "walk"): {"minutes": 40, "energy": -15, "credits": 0},
    ("cross", "transit"): {"minutes": 18, "energy": -6, "credits": 18},
}

# Entering/leaving a venue, or moving between venues, within one district:
# free and instant — places are rooms off the street, not journeys. Only
# district-to-district legs cost time.
LOCAL_COST = {"minutes": 0, "energy": 0, "credits": 0}

# Hovercab: door to door anywhere in the city, flat rate. Speed costs.
CAB_COST = {"minutes": 6, "energy": -2, "credits": 30}


def districts():
    return data.load("districts")


def are_adjacent(a, b):
    d = districts()
    return b in d.get(a, {}).get("adjacent", [])


def travel_cost(from_id, to_id, mode):
    """Cost between two places. Cabs fly door to door at a flat rate; on the
    ground, same-district moves (venue in/out) are instant regardless of
    mode, and district legs price by adjacency."""
    if mode == "cab":
        return {"distance": "cab", **CAB_COST}
    from_district = places.district_of(from_id)
    to_district = places.district_of(to_id)
    if from_district == to_district:
        return {"distance": "local", **LOCAL_COST}
    distance = "adjacent" if are_adjacent(from_district, to_district) else "cross"
    cost = TRAVEL_COST.get((distance, mode))
    if cost is None:
        raise GameError(f"Unknown travel mode: {mode!r}")
    return {"distance": distance, **cost}


def travel(player, clock, to_id, mode):
    """Move the player to another place (district or venue). Raises GameError
    on invalid destinations, closed venues, insufficient credits, or
    exhaustion. Returns the cost applied."""
    place = places.get(to_id)
    if place is None:
        raise GameError("There's no such place.")
    if to_id == player.location:
        raise GameError("You're already there.")
    if not places.is_open(to_id, clock):
        raise GameError(place.get("closed_line", f"{place['name']} is closed right now."))

    cost = dict(travel_cost(player.location, to_id, mode))
    # Species traits: Rooftop Lines halves walks; Priced In rides free.
    # Kettle Lightning (Gantry 9 tea) also quickens walks until midnight.
    if mode == "walk":
        mult = traits.effect(player, "walk_minutes_mult", 1.0)
        mult *= teahouse.effect(player, clock, "walk_minutes_mult", 1.0)
        cost["minutes"] = round(cost["minutes"] * mult)
    if mode == "transit" and traits.effect(player, "transit_free", False):
        cost["credits"] = 0
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
                "activity": window.get("activity"),
                "minutes_left": 0,
            }
        left = _minutes_left(now, end)
        tier = _tier(left)
        return {
            "available": tier != TIER_MISSED,
            "tier": tier,
            "location": window.get("location"),
            "district": district,
            "activity": window.get("activity"),
            "minutes_left": left,
        }
    return {
        "available": False,
        "tier": TIER_UNAVAILABLE,
        "location": None,
        "district": None,
        "activity": None,
        "minutes_left": 0,
    }
