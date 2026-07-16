"""The Lookout — Gantry 9's almanac board (a pure read model, no state).

Nine floors up, the terminus sees everything: where the cast is right now,
which venues have their lights on, what's on Vex's board today, and tonight's
Pit card. Composed server-side so the client stays a thin view — and so the
redaction rule lives in one place: the board shows *public* whereabouts and
schedules, never anyone's private numbers or undiscovered preferences.
"""

from game import arena, corps, fixer, places, world
from game.npc import NPC


def _place_name(place_id):
    place = places.get(place_id)
    return place["name"] if place else place_id


def compose(player, clock, day):
    people = []
    for _cid, npc in sorted(NPC.load_unlocked(player).items()):
        av = world.availability(npc, clock)
        # Schedule windows name a *place id* in "district" (which may be a
        # venue); "location" is only a sub-spot label like "the_floor".
        place_id = av.get("district")
        people.append(
            {
                "id": npc.id,
                "name": npc.name,
                "place": _place_name(place_id) if place_id else "Off the map",
                "activity": av.get("activity")
                or ("Out and about" if av["available"] else "Unaccounted for"),
                "available": av["available"],
            }
        )

    venue_rows = []
    for vid, venue in sorted(places.venues().items()):
        hours = venue.get("hours")
        venue_rows.append(
            {
                "id": vid,
                "name": venue["name"],
                "district": _place_name(venue["district"]),
                "open": places.is_open(vid, clock),
                "hours": f"{hours['open']}–{hours['close']}" if hours else "always open",
            }
        )

    gig = fixer.today_gig(day)
    bout = arena.next_bout(player)
    war = corps.war_state(clock.week)

    return {
        "time": clock.time_str,
        "week": clock.week,
        "day": clock.day,
        "people": people,
        "venues": venue_rows,
        "gig": {"id": gig["id"], "name": gig["name"], "brief": gig["brief"]},
        # This week's war, per the Triumvirate's own bulletins. Always.
        "war": {"line": war["line"], "bulletin": war["bulletin"]},
        "pit": {
            "wins": player.arena_wins,
            "next_number": bout["number"],
            "next_enemy": bout["enemy"]["name"],
            "next_title": bout["title"] if bout.get("championship") else None,
        },
    }
