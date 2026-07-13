"""Player inventory: owning and using items. (Milestone 6)

Inventory is a simple {item_id: quantity} map on the player (stored as a JSON
blob). Items come from data/items.json.
"""

from game import data
from game.errors import GameError
from game.player import MAX_ENERGY


def items():
    return data.load("items")


def get_item(item_id):
    item = items().get(item_id)
    if item is None:
        raise GameError("No such item.")
    return item


def quantity(player, item_id):
    return player.inventory.get(item_id, 0)


def add_item(player, item_id, qty=1):
    get_item(item_id)  # validate it exists
    player.inventory[item_id] = quantity(player, item_id) + qty


def remove_item(player, item_id, qty=1):
    have = quantity(player, item_id)
    if have < qty:
        raise GameError("You don't have that.")
    if have == qty:
        del player.inventory[item_id]
    else:
        player.inventory[item_id] = have - qty


def use_item(player, item_id):
    """Use a consumable (food). Applies its effects and consumes one. Returns a
    summary. Non-consumables can't be 'used'."""
    item = get_item(item_id)
    if item.get("type") != "food":
        raise GameError(f"You can't use the {item['name']} like that.")
    remove_item(player, item_id, 1)

    effects = item.get("effects", {})
    energy_gain = effects.get("energy", 0)
    if energy_gain:
        player.energy = min(MAX_ENERGY, player.energy + energy_gain)
    return {"item": item["name"], "energy": energy_gain}
