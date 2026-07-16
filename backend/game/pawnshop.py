"""Forget-Me-Not — the Shallows' pawnshop (data/pawnshop.json).

The other half of the economy: selling. The broker pays a fraction of the
sticker (rate x value x rarity), and what you sell doesn't vanish — it waits
on the shelf, redeemable at a markup, for hold_days. Then it's sold on and
the ledger closes. We remember so you don't have to.

Some things the shop won't hold: integrated hardware, habits, and other
people's bells — each refusal has its own line (data-driven).
"""

from game import data, inventory, places, shop
from game.errors import GameError


def _config():
    return data.load("pawnshop")


def _gate(player, clock):
    cfg = _config()
    if player.location != cfg["venue"]:
        raise GameError("The broker works out of Forget-Me-Not, in the Shallows.")
    if not places.is_open(cfg["venue"], clock):
        raise GameError(data.load("venues")[cfg["venue"]]["closed_line"])
    return cfg


def offer_for(item):
    """What the broker pays for an item (None = won't hold it)."""
    cfg = _config()
    if item["id"] in cfg["refusals"] or item.get("value", 0) <= 0:
        return None
    return max(1, round(shop.price(item) * cfg["rate"]))


def offers(player):
    """The broker's standing offers on everything the player carries."""
    all_items = inventory.items()
    result = {}
    for iid, qty in player.inventory.items():
        if qty <= 0 or iid not in all_items:
            continue
        offer = offer_for(all_items[iid])
        if offer is not None:
            result[iid] = offer
    return result


def shelf(player, day):
    """The player's shelf, pruning anything past its hold (sold on)."""
    cfg = _config()
    player.pawned = [e for e in player.pawned if day < e["day"] + cfg["hold_days"]]
    return [
        {
            **e,
            "days_left": e["day"] + cfg["hold_days"] - day,
            "name": inventory.get_item(e["item"])["name"],
        }
        for e in player.pawned
    ]


def sell(player, clock, item_id, day):
    """Pawn one item: credits now, a shelf entry until the hold runs out."""
    cfg = _gate(player, clock)
    if player.inventory.get(item_id, 0) <= 0:
        raise GameError("You're not carrying that.")
    item = inventory.get_item(item_id)
    refusal = cfg["refusals"].get(item_id)
    if refusal:
        raise GameError(refusal)
    paid = offer_for(item)
    if paid is None:
        raise GameError(
            'The broker turns it over once and slides it back. "Sentimental value only, friend."'
        )

    inventory.remove_item(player, item_id, 1)
    player.credits += paid
    player.pawned.append(
        {
            "item": item_id,
            "paid": paid,
            "buyback": max(1, round(paid * cfg["buyback_mult"])),
            "day": day,
        }
    )
    # The shelf only holds so much; the oldest gets sold on early.
    while len(player.pawned) > cfg["shelf_cap"]:
        player.pawned.pop(0)
    clock.advance(cfg["minutes"])
    return {"item": item_id, "name": item["name"], "paid": paid, "line": cfg["sell_line"]}


def buyback(player, clock, index, day):
    """Redeem a shelf entry by index (as listed by shelf())."""
    cfg = _gate(player, clock)
    entries = shelf(player, day)  # prunes first, so indices match the view
    if not isinstance(index, int) or not (0 <= index < len(entries)):
        raise GameError('The broker checks the ledger twice. "Not on my shelf."')
    entry = player.pawned[index]
    if player.credits < entry["buyback"]:
        raise GameError("The broker is sympathetic, but the ledger isn't.")
    player.credits -= entry["buyback"]
    player.pawned.pop(index)
    inventory.add_item(player, entry["item"], 1)
    clock.advance(cfg["minutes"])
    return {
        "item": entry["item"],
        "name": inventory.get_item(entry["item"])["name"],
        "paid": entry["buyback"],
        "line": cfg["buyback_line"],
    }
