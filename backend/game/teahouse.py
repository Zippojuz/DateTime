"""Gantry 9 — the rooftop-line terminus teahouse (data/teahouse.json).

Tea is a small daily ritual: one cup, poured at the gantry, and its effect
rides with you until midnight. Effect keys reuse the species-trait vocabulary
(walk_minutes_mult, dialogue_affection_bonus, ...) so any system that honors
traits can honor tea through the same kind of single resolution point — see
game/traits.py.
"""

from game import data
from game.errors import GameError
from game.player import MAX_ENERGY


def _config():
    return data.load("teahouse")


def menu():
    return _config()["menu"]


def day_index(clock):
    """Absolute in-game day — the tea's expiry key (mirrors app._day_index)."""
    return (clock.week - 1) * 7 + clock.day


def active(player, clock):
    """The tea spec working through the player right now, or None."""
    if player.tea_day != day_index(clock):
        return None
    return menu().get(player.tea_id)


def effect(player, clock, key, default):
    """Single resolution point for tea effects, mirroring traits.effect."""
    tea = active(player, clock)
    if tea is None:
        return default
    return tea["effects"].get(key, default)


def sip(player, clock, tea_id):
    """Take tea service at Gantry 9: one cup a day, a small cost, a small
    lift, and the cup's effect lasts until midnight."""
    cfg = _config()
    if player.location != cfg["venue"]:
        raise GameError("The kettles live at Gantry 9 — the pour doesn't travel.")
    tea = cfg["menu"].get(tea_id)
    if tea is None:
        raise GameError("That's not on the chalkboard.")
    if player.tea_day == day_index(clock):
        raise GameError("One cup a day. The chalkboard is very firm about this.")
    if player.credits < tea["cost"]:
        raise GameError("Not enough credits for the pour.")

    player.credits -= tea["cost"]
    player.energy = max(0, min(MAX_ENERGY, player.energy + cfg["energy"]))
    player.tea_day = day_index(clock)
    player.tea_id = tea_id
    clock.advance(cfg["minutes"])
    return {"id": tea_id, "name": tea["name"], "line": tea["pour_line"]}
