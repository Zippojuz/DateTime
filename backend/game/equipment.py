"""Equipment: JRPG gear slots with socketed gems (materia-style) + augments.

Ten gear slots: weapon, head, torso, arms, hands, legs, feet, two rings, and an
accessory. Gear gives flat stat bonuses and has 0-2 gem sockets. A gem's effect
depends on where it sits: an element gem in the WEAPON changes your basic
attack's element; the same gem in ARMOR resists that element. Stat/charge/xp/
credit gems work anywhere. The legendary Prisma Gem auto-targets weaknesses in
a weapon and resists all elements in armor.

Four AUGMENT slots (neural, ocular, dermal, skeletal) hold installed cyberware
(item type "augment"): passive body hardware granting stats, dodge, or heat
capacity/venting for wetware protocols. Augments have no gem sockets.

Ring items declare slot "ring" and fit either ring1 or ring2 (you can wear two).

Inventory is quantity-based (no per-item instances), so socketed gems live on
the equipped slot; unequipping returns the gear and its gems to the inventory
separately.
"""

from game import data, inventory
from game.errors import GameError

SLOTS = (
    "weapon",
    "head",
    "torso",
    "arms",
    "hands",
    "legs",
    "feet",
    "ring1",
    "ring2",
    "accessory",
    "aug_neural",
    "aug_ocular",
    "aug_dermal",
    "aug_skeletal",
)
STAT_KEYS = ("attack", "defense", "max_hp", "speed")
# Extra flat bonuses gear/augments may carry (dodge is a probability add).
EXTRA_KEYS = ("dodge", "heat_cap", "heat_vent")

AUG_SLOTS = ("aug_neural", "aug_ocular", "aug_dermal", "aug_skeletal")


def augment_capacity(player):
    """How many augments the player's lace can keep in sync at once — gated by
    hacking: 1 base, +1 per 5 points (hacking 15 runs all four slots)."""
    return min(len(AUG_SLOTS), 1 + player.attributes.get("hacking", 0) // 5)


def augments_installed(player):
    return sum(1 for slot in AUG_SLOTS if slot in player.equipment)


def _target_slot(player, item, requested=None):
    """Resolve which slot an item goes to. Rings fit ring1/ring2."""
    declared = item["slot"]
    if declared != "ring":
        if requested and requested != declared:
            raise GameError(f"That goes on the {declared} slot.")
        return declared
    if requested:
        if requested not in ("ring1", "ring2"):
            raise GameError("Rings go on a ring slot.")
        return requested
    # No preference: first empty ring finger, else replace ring1.
    for slot in ("ring1", "ring2"):
        if slot not in player.equipment:
            return slot
    return "ring1"


def equip(player, item_id, slot=None):
    """Equip a piece of gear (consumes it from inventory; swaps out whatever was
    in that slot, returning it and its gems). Returns the slot used."""
    item = inventory.get_item(item_id)
    if item.get("type") not in ("equipment", "augment"):
        raise GameError("That can't be equipped.")
    target = _target_slot(player, item, slot)
    # Hacking gates how many augments the lace can sync. Swapping within an
    # occupied slot is fine — the count doesn't grow.
    if item["type"] == "augment" and target not in player.equipment:
        cap = augment_capacity(player)
        if augments_installed(player) >= cap:
            raise GameError(
                f"Your lace can only sync {cap} augment{'s' if cap != 1 else ''} "
                f"at hacking {player.attributes.get('hacking', 0)} — train it higher."
            )
    inventory.remove_item(player, item_id, 1)
    if target in player.equipment:
        _return_to_inventory(player, target)
    player.equipment[target] = {"item": item_id, "gems": [None] * item.get("sockets", 0)}
    return target


def unequip(player, slot):
    """Remove the gear in a slot (gear + gems go back to inventory)."""
    if slot not in player.equipment:
        raise GameError("Nothing equipped there.")
    _return_to_inventory(player, slot)


def _return_to_inventory(player, slot):
    entry = player.equipment.pop(slot)
    inventory.add_item(player, entry["item"], 1)
    for gem_id in entry["gems"]:
        if gem_id:
            inventory.add_item(player, gem_id, 1)


def socket_gem(player, slot, gem_id, index):
    """Set a gem from inventory into an empty socket of equipped gear."""
    entry = player.equipment.get(slot)
    if not entry:
        raise GameError("Nothing equipped there.")
    gem = inventory.get_item(gem_id)
    if gem.get("type") != "gem":
        raise GameError("That's not a gem.")
    if not isinstance(index, int) or not (0 <= index < len(entry["gems"])):
        raise GameError("No such socket.")
    if entry["gems"][index]:
        raise GameError("That socket is already filled.")
    inventory.remove_item(player, gem_id, 1)
    entry["gems"][index] = gem_id


def unsocket_gem(player, slot, index):
    """Pop a gem out of a socket, back to inventory."""
    entry = player.equipment.get(slot)
    if (
        not entry
        or not isinstance(index, int)
        or not (0 <= index < len(entry["gems"]))
        or not entry["gems"][index]
    ):
        raise GameError("No gem there.")
    inventory.add_item(player, entry["gems"][index], 1)
    entry["gems"][index] = None


def bonuses(player):
    """Aggregate everything the current loadout grants."""
    total = {
        "attack": 0,
        "defense": 0,
        "max_hp": 0,
        "speed": 0,
        "dodge": 0.0,  # flat dodge-probability add (augments)
        "heat_cap": 0,  # extra protocol heat headroom
        "heat_vent": 0,  # extra heat shed per combat round
        "weapon_element": None,  # element gem in the weapon slot
        "auto_weakness": False,  # prisma in the weapon
        "resists": [],  # element gems in armor slots
        "resist_all": False,  # prisma in armor
        "charge_start": 0,
        "charge_max": 0,
        "xp_mult": 1.0,
        "credit_mult": 1.0,
    }
    items = data.load("items")
    for slot, entry in player.equipment.items():
        gear = items.get(entry["item"], {})
        for stat in STAT_KEYS + EXTRA_KEYS:
            total[stat] += gear.get("bonuses", {}).get(stat, 0)
        for gem_id in entry["gems"]:
            if not gem_id:
                continue
            effect = items.get(gem_id, {}).get("effect", {})
            for stat in STAT_KEYS:
                total[stat] += effect.get(stat, 0)
            if effect.get("element"):
                if slot == "weapon":
                    total["weapon_element"] = effect["element"]
                else:
                    total["resists"].append(effect["element"])
            if effect.get("prisma"):
                if slot == "weapon":
                    total["auto_weakness"] = True
                else:
                    total["resist_all"] = True
            total["charge_start"] += effect.get("charge_start", 0)
            total["charge_max"] += effect.get("charge_max", 0)
            total["xp_mult"] *= effect.get("xp_mult", 1.0)
            total["credit_mult"] *= effect.get("credit_mult", 1.0)
    return total
