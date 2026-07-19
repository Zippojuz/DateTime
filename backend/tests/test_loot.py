"""Loot drops, credit variance, dungeon-only items, and combat boosters."""

import pytest
from game import combat, data, inventory
from game.player import Player


def _player():
    return Player.create({"name": "Kai", "pronouns": "she/her"})


class DropRng:
    """Always drops; picks the first option; no crits/variance."""

    def uniform(self, a, b):
        return 1.0

    def random(self):
        return 0.0  # passes every chance gate (also always crits — fine here)

    def choice(self, seq):
        return seq[0]


class NoDropRng(DropRng):
    def random(self):
        return 0.99  # fails normal-tier drop chances; bosses (1.0) still drop


# --- Drop tables --------------------------------------------------------------


def test_normal_enemy_can_drop():
    enemy = data.load("enemies")["holo_siren"]  # tier 1 normal
    drops = combat.roll_drops(enemy, DropRng())
    assert drops == ["protein_cube"]


def test_normal_drop_can_miss():
    enemy = data.load("enemies")["holo_siren"]
    assert combat.roll_drops(enemy, NoDropRng()) == []


def test_miniboss_always_drops():
    enemy = data.load("enemies")["warden_lyss"]
    assert len(combat.roll_drops(enemy, NoDropRng())) == 1


def test_boss_drops_twice_guaranteed():
    enemy = data.load("enemies")["substrate_empress"]
    drops = combat.roll_drops(enemy, NoDropRng())
    assert len(drops) == 2


def test_all_loot_table_items_exist():
    items = {**data.load("items"), **data.load("books")}  # books are items too
    tables = data.load("loot")
    listed = list(tables["miniboss"]["items"]) + list(tables["boss"]["items"])
    for tier_table in tables["normal"].values():
        listed += tier_table["items"]
    for item_id in listed:
        assert item_id in items, f"loot table references unknown item {item_id}"


# --- Victory rewards ----------------------------------------------------------


def test_victory_includes_drops_and_credit_variance():
    p = _player()
    p.combat_level = 12
    state = combat.start(p, "warden_lyss", 1, 300)
    for _ in range(30):
        if state["over"]:
            break
        combat.act(p, state, "attack", rng=DropRng())
    assert state["victory"] is True
    rewards = state["rewards"]
    assert rewards["drops"], "miniboss must drop loot"
    # DropRng.uniform -> 1.0, so credits equal the base bounty exactly.
    assert rewards["credits"] == data.load("enemies")["warden_lyss"]["credits"]
    # The dropped item landed in the inventory.
    assert any(p.inventory.get(i, 0) for i in ("nano_patch", "charge_cell", "singing_crystal"))


# --- Dungeon-only items -------------------------------------------------------


def _all_shop_stock(shop_def):
    """Base stock, every cred tier's stock, and the whole rotating pool (the
    complete sellable catalog)."""
    ids = list(shop_def["stock"])
    for tier in shop_def.get("cred_tiers", []):
        ids.extend(tier["stock"])
    ids.extend(shop_def.get("rotates", {}).get("pool", []))
    return ids


def test_dungeon_only_items_not_sold_in_any_shop():
    items = data.load("items")
    shops = data.load("shops")
    dungeon_only = {iid for iid, item in items.items() if item.get("dungeon_only")}
    for shop_def in shops.values():
        overlap = dungeon_only.intersection(_all_shop_stock(shop_def))
        assert not overlap, f"{shop_def['name']} sells dungeon-only items: {overlap}"


def test_shop_stock_has_no_duplicate_items():
    # A duplicated item id renders as a React key collision (duplicated /
    # dropped rows in ShopPanel) — every shop's catalog (tiers included) must
    # be a set.
    for district_id, shop_def in data.load("shops").items():
        stock = _all_shop_stock(shop_def)
        dupes = {i for i in stock if stock.count(i) > 1}
        assert not dupes, f"{district_id} ({shop_def['name']}) lists duplicates: {dupes}"


def test_dungeon_gifts_work_with_preferences():
    from game import gifts
    from game.npc import NPC

    miko = NPC.load("miko")  # loves music
    crystal = data.load("items")["singing_crystal"]  # rare music gift
    react = gifts.reaction(crystal, miko)
    assert react["delta"] == 8  # love(6) + rare(2)


# --- Boosters (combat-only charge items) ---------------------------------------


def test_booster_restores_charge_in_combat():
    p = _player()
    inventory.add_item(p, "charge_cell", 1)
    state = combat.start(p, "holo_siren", 1, 60)
    state["charge"] = 0
    combat.act(p, state, "item", item_id="charge_cell", rng=NoDropRng())
    # +3 from the cell, +1 end-of-turn regen.
    assert state["charge"] == 4
    assert "charge_cell" not in p.inventory


def test_booster_cannot_be_used_outside_combat():
    p = _player()
    inventory.add_item(p, "charge_cell", 1)
    with pytest.raises(Exception):
        inventory.use_item(p, "charge_cell")
