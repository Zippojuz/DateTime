"""The daily action loop. (Milestone 1)

A deliberately minimal action set that exercises the time + energy systems.
Real activities (jobs, hangouts, dates, shopping) layer in with later
milestones and their own data. Time/energy costs follow the design doc.

`energy` is an int delta, or the string "full" to restore to max.
"""

from game import data, teahouse, traits
from game.errors import GameError
from game.player import MAX_ENERGY

DAYLIGHT = (6 * 60, 18 * 60)  # photosynthesis window

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

    minutes, energy = action["minutes"], action["energy"]
    if action.get("trains"):
        rates = house_rates(player, attribute)
        if rates:
            minutes, energy = rates["minutes"], rates["energy"]

    # Species traits reshape the daily loop (see game/traits.py).
    if action_id == "rest":
        minutes = traits.effect(player, "rest_minutes", minutes)  # Maintenance Cycle
    sun = traits.effect(player, "photosynthesis", 0)
    if sun and action_id in ("wait", "explore") and _daylight(clock):
        energy = sun  # Photosynthesis: daylight idling feeds you
    if isinstance(energy, int) and energy < 0:
        mult = traits.effect(player, "action_energy_mult", 1.0)  # Shift Change
        energy = round(energy * mult)

    _apply_energy(player, energy)

    if action.get("trains"):
        _train(player, attribute, clock)

    clock.advance(minutes)
    return player, clock


def _daylight(clock):
    return DAYLIGHT[0] <= clock.minute_of_day < DAYLIGHT[1]


def house_rates(player, attribute):
    """Venue coaching: a venue may discount training for its listed attributes
    (the Hold coaches Agility and Courage). None when no discount applies."""
    venue = data.load("venues").get(player.location)
    rates = (venue or {}).get("training")
    if rates and attribute in rates["attributes"]:
        return rates
    return None


def _apply_energy(player, rule):
    if rule == "full":
        player.energy = MAX_ENERGY
        return
    if player.energy + rule < 0:
        raise GameError("Too tired for that — rest first.")
    player.energy = max(0, min(MAX_ENERGY, player.energy + rule))


def _train(player, attribute, clock):
    registry = data.attributes()
    if attribute not in registry:
        raise GameError("Choose a valid attribute to train.")
    spec = registry[attribute]
    # Overclock Oolong (Gantry 9): today's sessions stick a little harder.
    gain = 1 + teahouse.effect(player, clock, "train_bonus", 0)
    player.attributes[attribute] = min(spec["max"], player.attributes[attribute] + gain)
