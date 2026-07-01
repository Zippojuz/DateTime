"""District hours, NPC availability, and travel. (Milestone 2 / 3)

Milestone 2 uses the schedule-based availability resolver so the player can talk
to whoever is currently around. District travel + the map arrive in Milestone 3.
"""

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
        if not window.get("available", True):
            return {
                "available": False,
                "tier": TIER_UNAVAILABLE,
                "location": window.get("location"),
                "minutes_left": 0,
            }
        left = _minutes_left(now, end)
        tier = _tier(left)
        return {
            "available": tier != TIER_MISSED,
            "tier": tier,
            "location": window.get("location"),
            "minutes_left": left,
        }
    return {
        "available": False,
        "tier": TIER_UNAVAILABLE,
        "location": None,
        "minutes_left": 0,
    }
