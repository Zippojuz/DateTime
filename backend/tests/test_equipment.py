"""Equipment slots, gem socketing (materia-style), and combat integration."""

import pytest
from game import combat, equipment, inventory
from game.errors import GameError
from game.player import Player


def _player(**gear):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    return p


class QuietRng:
    def uniform(self, a, b):
        return 1.0

    def random(self):
        return 0.99

    def choice(self, seq):
        return seq[0]


# --- Equip / unequip ----------------------------------------------------------


def test_equip_moves_gear_from_inventory_to_slot():
    p = _player()
    inventory.add_item(p, "arc_blade", 1)
    slot = equipment.equip(p, "arc_blade")
    assert slot == "weapon"
    assert p.equipment["weapon"]["item"] == "arc_blade"
    assert p.equipment["weapon"]["gems"] == [None]  # one socket
    assert "arc_blade" not in p.inventory


def test_equip_swaps_and_returns_old_gear_with_gems():
    p = _player()
    inventory.add_item(p, "arc_blade", 1)
    inventory.add_item(p, "ember_gem", 1)
    inventory.add_item(p, "pulse_pistol", 1)
    equipment.equip(p, "arc_blade")
    equipment.socket_gem(p, "weapon", "ember_gem", 0)
    equipment.equip(p, "pulse_pistol")  # swap
    # Old blade AND its gem came back.
    assert p.inventory.get("arc_blade") == 1
    assert p.inventory.get("ember_gem") == 1
    assert p.equipment["weapon"]["item"] == "pulse_pistol"


def test_cannot_equip_non_equipment():
    p = _player()
    with pytest.raises(GameError):
        equipment.equip(p, "protein_cube")


def test_two_rings_fill_both_fingers():
    p = _player()
    inventory.add_item(p, "signal_ring", 2)
    assert equipment.equip(p, "signal_ring") == "ring1"
    assert equipment.equip(p, "signal_ring") == "ring2"
    assert p.equipment["ring1"]["item"] == "signal_ring"
    assert p.equipment["ring2"]["item"] == "signal_ring"


def test_all_declared_slots_are_known():
    from game import data

    for item in data.load("items").values():
        if item.get("type") == "equipment":
            slot = item["slot"]
            assert slot == "ring" or slot in equipment.SLOTS, f"unknown slot {slot}"


# --- Sockets --------------------------------------------------------------------


def test_socket_and_unsocket_conserve_gems():
    p = _player()
    inventory.add_item(p, "arc_blade", 1)
    inventory.add_item(p, "power_gem", 1)
    equipment.equip(p, "arc_blade")
    equipment.socket_gem(p, "weapon", "power_gem", 0)
    assert "power_gem" not in p.inventory
    equipment.unsocket_gem(p, "weapon", 0)
    assert p.inventory["power_gem"] == 1
    assert p.equipment["weapon"]["gems"] == [None]


def test_cannot_socket_into_full_or_missing_socket():
    p = _player()
    inventory.add_item(p, "arc_blade", 1)
    inventory.add_item(p, "power_gem", 2)
    equipment.equip(p, "arc_blade")
    equipment.socket_gem(p, "weapon", "power_gem", 0)
    with pytest.raises(GameError):
        equipment.socket_gem(p, "weapon", "power_gem", 0)  # full
    with pytest.raises(GameError):
        equipment.socket_gem(p, "weapon", "power_gem", 5)  # no such socket


def test_cannot_socket_non_gem():
    p = _player()
    inventory.add_item(p, "arc_blade", 1)
    inventory.add_item(p, "protein_cube", 1)
    equipment.equip(p, "arc_blade")
    with pytest.raises(GameError):
        equipment.socket_gem(p, "weapon", "protein_cube", 0)


# --- Stats & combat integration --------------------------------------------------


def test_gear_and_gems_raise_stats():
    p = _player()
    base = combat.player_stats(p)
    inventory.add_item(p, "arc_blade", 1)
    inventory.add_item(p, "power_gem", 1)
    equipment.equip(p, "arc_blade")
    equipment.socket_gem(p, "weapon", "power_gem", 0)
    geared = combat.player_stats(p)
    assert geared["attack"] == base["attack"] + 4 + 3  # blade + gem


def test_element_gem_in_weapon_changes_attack_element():
    p = _player()
    inventory.add_item(p, "arc_blade", 1)
    inventory.add_item(p, "ember_gem", 1)
    equipment.equip(p, "arc_blade")
    equipment.socket_gem(p, "weapon", "ember_gem", 0)
    # Thermal attack vs a cryo enemy hits the weakness.
    assert combat.attack_element(p, "cryo") == "thermal"
    state = combat.start(p, "cryo_duelist", 4, 200)
    combat.act(p, state, "attack", rng=QuietRng())
    assert any("weakness" in line for line in state["log"])


def test_element_gem_in_armor_resists():
    p = _player()
    inventory.add_item(p, "signal_ring", 1)
    inventory.add_item(p, "ember_gem", 1)
    equipment.equip(p, "signal_ring")
    equipment.socket_gem(p, "ring1", "ember_gem", 0)
    assert combat.incoming_resist(p, "thermal") == 0.5
    assert combat.incoming_resist(p, "cryo") == 1.0


def test_prisma_gem_is_the_super_gem():
    p = _player()
    inventory.add_item(p, "arc_blade", 1)
    inventory.add_item(p, "signal_ring", 1)
    inventory.add_item(p, "prisma_gem", 2)
    equipment.equip(p, "arc_blade")
    equipment.socket_gem(p, "weapon", "prisma_gem", 0)
    # In the weapon: auto-targets whatever the enemy is weak to.
    assert combat.attack_element(p, "cryo") == "thermal"
    assert combat.attack_element(p, "kinetic") == "psionic"
    # In armor: resists everything.
    equipment.equip(p, "signal_ring")
    equipment.socket_gem(p, "ring1", "prisma_gem", 0)
    assert combat.incoming_resist(p, "voltaic") == 0.5
    assert combat.incoming_resist(p, "toxin") == 0.5


def test_surge_gem_raises_charge():
    p = _player()
    inventory.add_item(p, "signal_ring", 1)
    inventory.add_item(p, "surge_gem", 1)
    equipment.equip(p, "signal_ring")
    equipment.socket_gem(p, "ring1", "surge_gem", 0)
    state = combat.start(p, "holo_siren", 1, 100)
    assert state["charge"] == combat.CHARGE_START + 1
    assert state["charge_max"] == combat.CHARGE_MAX + 1


def test_fortune_and_sage_gems_multiply_rewards():
    def win_rewards(gem):
        p = _player()
        p.combat_level = 12
        if gem:
            inventory.add_item(p, "signal_ring", 1)
            inventory.add_item(p, gem, 1)
            equipment.equip(p, "signal_ring")
            equipment.socket_gem(p, "ring1", gem, 0)
        state = combat.start(p, "holo_siren", 1, 300)
        for _ in range(20):
            if state["over"]:
                break
            combat.act(p, state, "attack", rng=QuietRng())
        return state["rewards"]

    plain = win_rewards(None)
    assert win_rewards("fortune_gem")["credits"] > plain["credits"]
    assert win_rewards("sage_gem")["xp"] > plain["xp"]


# --- Loot integrity ---------------------------------------------------------------


def test_boss_jackpot_can_drop_super_rares():
    from game import data

    class JackpotRng(QuietRng):
        def random(self):
            return 0.0  # every roll passes, including the 12% jackpot

    enemy = data.load("enemies")["substrate_empress"]
    drops = combat.roll_drops(enemy, JackpotRng())
    assert len(drops) == 3  # 2 guaranteed + jackpot
    assert drops[-1] in ("prisma_gem", "empress_heart")


def test_loot_bonus_pool_items_exist():
    from game import data

    items = data.load("items")
    bonus = data.load("loot")["boss"]["bonus"]
    for item_id in bonus["items"]:
        assert item_id in items
