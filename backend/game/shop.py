"""Shops: spend credits to buy items. (Milestone 6)

Each place's market (data/shops.json, keyed by district or venue id) stocks a
subset of items at a price modifier. Price scales with rarity — a legendary
costs far more than a common of the same base value.

A shop may also carry ``cred_tiers``: back-room stock gated by street cred
(the Static Bazaar's Back Shelf / Locked Case / Basement). Locked tiers show
as teasers; their goods can't be browsed or bought until the dealer knows
your name.

A shop may also ``rotate``: the Night Market draws a few extra stalls from a
pool each night, deterministically by day — miss tonight's find and it's gone
for a while.
"""

import random as _random

from game import data, inventory, traits
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


def _priced(item_ids, price_mod):
    all_items = inventory.items()
    return [
        {**all_items[iid], "price": price(all_items[iid], price_mod)}
        for iid in item_ids
        if iid in all_items
    ]


def rotating_ids(shop, day):
    """Tonight's rotating stalls (deterministic per absolute day)."""
    spec = shop.get("rotates")
    if not spec or day is None:
        return []
    rng = _random.Random(f"stalls:{day}")
    return rng.sample(spec["pool"], min(spec["count"], len(spec["pool"])))


def _purchasable_ids(shop, cred, day=None):
    """Every item id the player can actually buy here at their cred, today."""
    ids = list(shop["stock"]) + rotating_ids(shop, day)
    for tier in shop.get("cred_tiers", []):
        if cred >= tier["cred"]:
            ids.extend(tier["stock"])
    return ids


def _effective_mod(shop, discount):
    """The district price mod after any player discount (Priced In)."""
    return shop["price_mod"] * (1 - discount)


def stock(district_id, cred=0, discount=0.0, day=None):
    """Items for sale at a place, with computed prices (tier stock is
    reported separately via ``tiers``). Rotating stalls are flagged
    ``tonight`` so the UI can badge them. Empty if no shop."""
    shop = _shop_for(district_id)
    if not shop:
        return []
    mod = _effective_mod(shop, discount)
    listed = _priced(shop["stock"], mod)
    listed.extend({**entry, "tonight": True} for entry in _priced(rotating_ids(shop, day), mod))
    return listed


def tiers(district_id, cred=0, discount=0.0):
    """The shop's cred-gated back rooms: unlocked tiers carry priced stock,
    locked ones only their tease (and the cred the dealer expects)."""
    shop = _shop_for(district_id)
    if not shop:
        return []
    result = []
    for tier in shop.get("cred_tiers", []):
        unlocked = cred >= tier["cred"]
        entry = {"name": tier["name"], "cred": tier["cred"], "unlocked": unlocked}
        if unlocked:
            entry["stock"] = _priced(tier["stock"], _effective_mod(shop, discount))
        else:
            entry["tease"] = tier["tease"]
            entry["count"] = len(tier["stock"])
        result.append(entry)
    return result


def buy(player, clock, item_id):
    """Buy an item from the shop where the player stands. Raises GameError if the
    item isn't stocked here, is behind a cred tier the player hasn't earned, or
    they can't afford it. Returns a summary."""
    shop = _shop_for(player.location)
    if not shop:
        raise GameError("That isn't sold here.")
    day = (clock.week - 1) * 7 + clock.day
    if item_id not in _purchasable_ids(shop, player.street_cred, day):
        # Distinguish "behind a locked tier" from "not sold at all".
        for tier in shop.get("cred_tiers", []):
            if item_id in tier["stock"]:
                raise GameError(
                    "The dealer's eyes slide past you like you're furniture. "
                    f"({tier['name']} opens at {tier['cred']} cred.)"
                )
        raise GameError("That isn't sold here.")
    item = inventory.get_item(item_id)
    mod = _effective_mod(shop, traits.effect(player, "shop_discount", 0.0))
    cost = price(item, mod)
    if player.credits < cost:
        raise GameError("You can't afford that.")

    player.credits -= cost
    inventory.add_item(player, item_id, 1)
    clock.advance(SHOP_MINUTES)
    return {"item": item["name"], "cost": cost}
