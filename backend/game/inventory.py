"""Player inventory: owning and using items. (Milestone 6)

Inventory is a simple {item_id: quantity} map on the player (stored as a JSON
blob). Items come from data/items.json.
"""

from game import data
from game.errors import GameError
from game.player import MAX_ENERGY


def items():
    """The full item registry. Books live in their own file (data/books.json)
    but are carriable items too, so they're merged in here — every system that
    resolves items (loot, pawn, shop, gifts, ...) sees them for free."""
    return {**data.load("items"), **data.load("books")}


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
    """Use a consumable: food restores energy; a data-shard burns its wetware
    protocol into your lace (permanent, consumed). Returns a summary."""
    item = get_item(item_id)

    if item.get("type") == "shard":
        protocol_id = item["teaches"]
        protocol = data.load("protocols")[protocol_id]
        if protocol_id in player.protocols:
            raise GameError(f"Your lace already runs {protocol['name']}.")
        remove_item(player, item_id, 1)
        player.protocols.append(protocol_id)
        return {"item": item["name"], "energy": 0, "learned": protocol["name"]}

    if item.get("type") != "food":
        raise GameError(f"You can't use the {item['name']} like that.")
    remove_item(player, item_id, 1)

    effects = item.get("effects", {})
    energy_gain = effects.get("energy", 0)
    if energy_gain:
        player.energy = min(MAX_ENERGY, player.energy + energy_gain)
    return {"item": item["name"], "energy": energy_gain}
