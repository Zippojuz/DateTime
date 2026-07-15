"""Random street encounters during travel. (Milestone 3)

Deliberately shallow for now: flavor moments, a merchant you can't yet trade
with, trouble you walk past, or a sighting of someone you've already met (a tiny
affection bump). Real quest chains come later.

Randomness lives here (server-side Python `random` is fine). The resolver takes
an injectable `rng` so tests can seed it.
"""

import random as _random

from game import corps, data

# Chance that travel produces any encounter at all (luck nudges it up).
ENCOUNTER_CHANCE = 0.6
ENCOUNTER_PER_LUCK = 0.01
ENCOUNTER_CAP = 0.9

# Weighted kinds (flavor is common; the Triumvirate's ads are inescapable).
_KINDS = ["flavor", "flavor", "flavor", "sighting", "merchant", "trouble", "ad"]

SIGHTING_AFFECTION = 1


def _corp_ad(lines, week, rng):
    """An intrusive Triumvirate ad, personalized in the worst way."""
    corp = rng.choice(sorted(data.load("corps").values(), key=lambda c: c["id"]))
    war = corps.war_state(week)
    text = (
        rng.choice(lines["ad"])
        .replace("{name}", corp["name"])
        .replace("{slogan}", corp["slogan"])
        .replace("{sector}", corp["sector"])
        .replace("{war}", war["line"])
    )
    return {"type": "ad", "corp": corp["id"], "text": text}


def roll_encounter(present_npcs, met_ids, rng=None, luck=0, week=1):
    """Return an encounter dict or None.

    present_npcs: {npc_id: name} available in the destination right now.
    met_ids: set of npc_ids the player has already met (eligible for sightings).
    luck: the traveler's luck — lucky people run into things.
    week: current in-game week (drives the Triumvirate's rotating "war").
    """
    rng = rng or _random
    if rng.random() > min(ENCOUNTER_CAP, ENCOUNTER_CHANCE + luck * ENCOUNTER_PER_LUCK):
        return None

    lines = data.load("encounters")
    kind = rng.choice(_KINDS)
    if kind == "ad":
        return _corp_ad(lines, week, rng)

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
