"""Seasonal calendar events. (Milestone 4)

Events are date-gated: each fires once when the clock reaches its (week, day).
For now they surface as notifications/flavor; deeper event scenes (choices,
dedicated dialogue) come later. Firing state lives on the player
(``fired_events``), threaded through the routes that advance the clock.
"""

from game import data


def _reached(clock, event):
    return (clock.week, clock.day) >= (event.get("week", 1), event.get("day", 1))


def due_events(clock, fired):
    """Return events whose date has arrived and that haven't fired yet, sorted
    by their scheduled date."""
    events = data.load("events")
    pending = [
        ev for ev in events.values() if ev["id"] not in fired and _reached(clock, ev)
    ]
    return sorted(pending, key=lambda e: (e.get("week", 1), e.get("day", 1)))


def fire_due(player, clock):
    """Fire any newly-due events, recording them on the player. Returns the list
    of events that fired this call (possibly empty)."""
    newly = due_events(clock, player.fired_events)
    for event in newly:
        player.fired_events.append(event["id"])
    return newly
