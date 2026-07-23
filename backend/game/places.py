"""Places — districts, and the venues nested inside them.

A *place* is anywhere the player can stand: one of the five districts, or a
venue (data/venues.json) tucked inside one — the Pit under the Grid today;
gyms, libraries, and back rooms later. ``player.location`` holds a place id of
either kind.

Two resolution rules keep the model simple:
- Rules about *the neighborhood* (travel cost, adjacency) resolve through
  ``district_of()``.
- Rules about *the room* (who you can reach, what's for sale, where a fight
  can start) compare place ids exactly — being inside the Pit is not the same
  as standing in the Grid above it.

Venues may keep hours; districts never close.
"""

from game import data


def districts():
    return data.load("districts")


def venues():
    return data.load("venues")


def homes():
    # Residences (data/homes.json) are places too — you travel to your home to
    # sleep. Loaded directly (not via game.house) to avoid an import cycle.
    return data.load("homes")


def is_venue(place_id):
    return place_id in venues()


def get(place_id):
    """The district, venue, or home entry for a place id (None if none)."""
    return districts().get(place_id) or venues().get(place_id) or homes().get(place_id)


def district_of(place_id):
    """The district a place belongs to (a district is its own district)."""
    place = venues().get(place_id) or homes().get(place_id)
    return place["district"] if place else place_id


def venues_in(district_id):
    return {vid: v for vid, v in venues().items() if v["district"] == district_id}


def _to_minutes(hhmm):
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def is_open(place_id, clock):
    """Whether a place is open right now. Districts (and venues without
    hours) are always open; venue hours may cross midnight."""
    venue = venues().get(place_id)
    if venue is None or "hours" not in venue:
        return True
    now = clock.minute_of_day
    start = _to_minutes(venue["hours"]["open"])
    end = _to_minutes(venue["hours"]["close"])
    if start <= end:
        return start <= now < end
    return now >= start or now < end
