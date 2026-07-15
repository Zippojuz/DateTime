"""Mama Vex's gig board: gray-market work above the day-job economy.

One gig on offer per day (rotating through data/gigs.json), taken in the
Docking Quarter while Vex is holding court. Every gig forks: the clean choice
pays fair; the dirty choice pays better and costs something that isn't money —
usually a cast member's opinion of you (applied by the route via social).
"""

from game import data
from game.errors import GameError

GIG_DISTRICT = "docking_quarter"


def today_gig(day_index):
    """The gig on Vex's board today (deterministic daily rotation)."""
    gigs = list(data.load("gigs").values())
    return gigs[(day_index - 1) % len(gigs)]


def run_gig(player, clock, day_index, gig_id, choice_index):
    """Work today's gig. Applies time/energy/pay and marks the day; the caller
    applies the choice's social effects. Returns the chosen branch."""
    gig = today_gig(day_index)
    if gig["id"] != gig_id:
        raise GameError("That job's off the board — ask Vex what's on today.")
    if player.last_gig_day == day_index:
        raise GameError('Vex runs one gig a day. "Pace yourself, line item."')
    if player.location != GIG_DISTRICT:
        raise GameError("Gigs start at Vex's table in the Docking Quarter.")
    if not isinstance(choice_index, int) or not (0 <= choice_index < len(gig["choices"])):
        raise GameError("Pick how you're playing it.")
    if player.energy < gig["energy"]:
        raise GameError("Too tired for Vex's kind of work — rest first.")

    choice = gig["choices"][choice_index]
    player.energy -= gig["energy"]
    player.credits += choice["pay"]
    player.last_gig_day = day_index
    clock.advance(gig["minutes"])
    return choice
