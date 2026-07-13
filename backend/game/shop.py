"""Shops: spend credits to buy items. (Milestone 6)

Each district's market (data/shops.json) stocks a subset of items at a district
price modifier. Price scales with rarity — a legendary costs far more than a
common of the same base value.
"""

from game import data, inventory
from game.errors import GameError

# Rarity's price multiplier, on top of an item's base value.
RARITY_PRICE_MULT = {"common": 1, "uncommon": 3, "rare": 8, "legendary": 20}

# Browsing a stall costs a little game time.
SHOP_MINUTES = 30


def _shop_for(district_id):
    return data.load("shops").get(district_id)


def price(item, price_mod=1.0):
    mult = RARITY_PRICE_MULT.get(item.get("rarity", "common"), 1)
    return round(item["value"] * mult * price_mod)


def stock(district_id):
    """Items for sale in a district, with computed prices. Empty if no shop."""
    shop = _shop_for(district_id)
    if not shop:
        return []
    all_items = inventory.items()
    return [
        {**all_items[iid], "price": price(all_items[iid], shop["price_mod"])}
        for iid in shop["stock"]
        if iid in all_items
    ]


def buy(player, clock, item_id):
    """Buy an item from the shop where the player stands. Raises GameError if the
    item isn't stocked here or you can't afford it. Returns a summary."""
    shop = _shop_for(player.location)
    if not shop or item_id not in shop["stock"]:
        raise GameError("That isn't sold here.")
    item = inventory.get_item(item_id)
    cost = price(item, shop["price_mod"])
    if player.credits < cost:
        raise GameError("You can't afford that.")

    player.credits -= cost
    inventory.add_item(player, item_id, 1)
    clock.advance(SHOP_MINUTES)
    return {"item": item["name"], "cost": cost}
