"""The Tide Line — salvage runs in the flooded levels (data/tide_line.json).

Only passable at slack water (04:00–06:00 — the venue's hours do the gating).
A run is thirty cold minutes and a roll on the event table: honest flotsam,
a sealed crate, a hazard that takes instead of gives, empty water, the rare
tide glass — and, sometimes, a far figure walking the water line who doesn't
look your way.
"""

import random as _random_module

from game import data, inventory, places
from game.errors import GameError

_random = _random_module.Random()


def _config():
    return data.load("tide_line")


def run(player, clock, rng=None):
    """Wade one salvage run. Returns {id, text, ...effects}."""
    rng = rng or _random
    cfg = _config()
    if player.location != cfg["venue"]:
        raise GameError("The flooded levels are under the Docking Quarter — find the hatch.")
    if not places.is_open(cfg["venue"], clock):
        raise GameError(data.load("venues")[cfg["venue"]]["closed_line"])
    cost = cfg["run"]
    if player.energy + cost["energy"] < 0:
        raise GameError("Too tired to argue with cold water — rest first.")

    player.energy = max(0, player.energy + cost["energy"])
    clock.advance(cost["minutes"])

    events = cfg["events"]
    event = rng.choices(events, weights=[e["weight"] for e in events], k=1)[0]
    return _resolve(player, event, rng)


def _resolve(player, event, rng):
    """Apply one event's effects; returns the outcome payload."""
    outcome = {"id": event["id"], "text": event["text"]}
    if "credits" in event:
        lo, hi = event["credits"]
        found = rng.randint(lo, hi)
        player.credits += found
        outcome["credits"] = found
    if "items" in event:
        item_id = rng.choice(event["items"])
        inventory.add_item(player, item_id, 1)
        outcome["item"] = item_id
        outcome["item_name"] = inventory.get_item(item_id)["name"]
    if "item" in event:
        inventory.add_item(player, event["item"], 1)
        outcome["item"] = event["item"]
        outcome["item_name"] = inventory.get_item(event["item"])["name"]
    if "energy" in event:  # a hazard takes instead of gives
        player.energy = max(0, player.energy + event["energy"])
        outcome["energy"] = event["energy"]
    return outcome
