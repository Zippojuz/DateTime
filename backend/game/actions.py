"""The daily action loop. (Milestone 1)

A deliberately minimal action set that exercises the time + energy systems.
Real activities (jobs, hangouts, dates, shopping) layer in with later
milestones and their own data. Time/energy costs follow the design doc.

`energy` is an int delta, or the string "full" to restore to max.
"""

from game import data
from game.errors import GameError
from game.player import MAX_ENERGY

ACTIONS = {
    "rest": {"label": "Rest (full sleep)", "minutes": 480, "energy": "full"},
    "nap": {"label": "Nap", "minutes": 120, "energy": 30},
    "explore": {"label": "Explore", "minutes": 60, "energy": -10},
    "train": {"label": "Train a stat", "minutes": 120, "energy": -15, "trains": True},
    "wait": {"label": "Wait", "minutes": 60, "energy": 0},
}


def apply_action(player, clock, action_id, attribute=None):
    """Apply an action to the player + clock in place. Raises GameError on
    invalid actions or insufficient energy."""
    action = ACTIONS.get(action_id)
    if action is None:
        raise GameError(f"Unknown action: {action_id!r}")

    _apply_energy(player, action["energy"])

    if action.get("trains"):
        _train(player, attribute)

    clock.advance(action["minutes"])
    return player, clock


def _apply_energy(player, rule):
    if rule == "full":
        player.energy = MAX_ENERGY
        return
    if player.energy + rule < 0:
        raise GameError("Too tired for that — rest first.")
    player.energy = max(0, min(MAX_ENERGY, player.energy + rule))


def _train(player, attribute):
    registry = data.attributes()
    if attribute not in registry:
        raise GameError("Choose a valid attribute to train.")
    spec = registry[attribute]
    player.attributes[attribute] = min(spec["max"], player.attributes[attribute] + 1)
