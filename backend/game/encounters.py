"""Random street encounters during travel. (Milestone 3)

Deliberately shallow for now: flavor moments, a merchant you can't yet trade
with, trouble you walk past, or a sighting of someone you've already met (a tiny
affection bump). Real quest chains come later.

Randomness lives here (server-side Python `random` is fine). The resolver takes
an injectable `rng` so tests can seed it.
"""

import random as _random

from game import data

# Chance that travel produces any encounter at all (luck nudges it up).
ENCOUNTER_CHANCE = 0.6
ENCOUNTER_PER_LUCK = 0.01
ENCOUNTER_CAP = 0.9

# Weighted kinds (flavor is common).
_KINDS = ["flavor", "flavor", "flavor", "sighting", "merchant", "trouble"]

SIGHTING_AFFECTION = 1


def roll_encounter(present_npcs, met_ids, rng=None, luck=0):
    """Return an encounter dict or None.

    present_npcs: {npc_id: name} available in the destination right now.
    met_ids: set of npc_ids the player has already met (eligible for sightings).
    luck: the traveler's luck — lucky people run into things.
    """
    rng = rng or _random
    if rng.random() > min(ENCOUNTER_CAP, ENCOUNTER_CHANCE + luck * ENCOUNTER_PER_LUCK):
        return None

    lines = data.load("encounters")
    kind = rng.choice(_KINDS)

    if kind == "sighting":
        seen = [nid for nid in present_npcs if nid in met_ids]
        if seen:
            npc_id = rng.choice(seen)
            text = rng.choice(lines["sighting"]).replace("{name}", present_npcs[npc_id])
            return {
                "type": "sighting",
                "npc_id": npc_id,
                "text": text,
                "affection": SIGHTING_AFFECTION,
            }
        kind = "flavor"  # no one to spot → fall back to flavor

    return {"type": kind, "text": rng.choice(lines[kind])}
