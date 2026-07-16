"""The Steeps' paid soak — the fast, expensive cousin of sleep.

Ninety minutes in the terraced pools restores full energy: a third of the
time a night's rest costs, for credits instead of hours. The soak block
lives on the venue entry (data/venues.json), like training does.
"""

from game import data, places
from game.errors import GameError
from game.player import MAX_ENERGY


def soak(player, clock):
    venue = data.load("venues")["the_steeps"]
    spec = venue["soak"]
    if player.location != venue["id"]:
        raise GameError("The pools are at the Steeps, in the Bloom District.")
    if not places.is_open(venue["id"], clock):
        raise GameError(venue["closed_line"])
    if player.credits < spec["cost"]:
        raise GameError("The attendant is sympathetic, but the water isn't free.")
    player.credits -= spec["cost"]
    player.energy = MAX_ENERGY
    clock.advance(spec["minutes"])
    return {"line": spec["line"], "minutes": spec["minutes"], "cost": spec["cost"]}
