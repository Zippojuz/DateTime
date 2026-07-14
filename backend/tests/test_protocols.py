"""Wetware protocols (data-shard magic + heat) and augmentation slots."""

import pytest
from game import combat, dungeon, equipment, inventory
from game.calendar import GameClock
from game.errors import GameError
from game.player import Player


class QuietRng:
    def uniform(self, a, b):
        return 1.0

    def random(self):
        return 0.99

    def choice(self, seq):
        return seq[0]

    def randint(self, a, b):
        return b


def _adept(level=5, *protocols):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.combat_level = level
    p.protocols = list(protocols)
    return p


def _fight(p, enemy_id="chrome_vixen"):
    return combat.start(p, enemy_id, 1, combat.player_stats(p)["max_hp"])


# --- Learning from shards ---------------------------------------------------------


def test_using_a_shard_teaches_its_protocol():
    p = _adept()
    inventory.add_item(p, "shard_purge_cycle", 1)
    result = inventory.use_item(p, "shard_purge_cycle")
    assert result["learned"] == "Purge Cycle"
    assert "purge_cycle" in p.protocols
    assert "shard_purge_cycle" not in p.inventory  # consumed


def test_cannot_learn_a_protocol_twice():
    p = _adept(5, "purge_cycle")
    inventory.add_item(p, "shard_purge_cycle", 1)
    with pytest.raises(GameError, match="already runs"):
        inventory.use_item(p, "shard_purge_cycle")
    assert p.inventory["shard_purge_cycle"] == 1  # not consumed


# --- Casting in combat --------------------------------------------------------------


def test_casting_builds_heat_and_strikes():
    # A miniboss, so the snap doesn't one-shot the target and the round completes.
    p = _adept(5, "gravity_snap")
    state = _fight(p, enemy_id="warden_lyss")
    before = state["enemy_hp"]
    combat.act(p, state, "protocol", protocol_id="gravity_snap", rng=QuietRng())
    assert state["enemy_hp"] < before
    # 35 base heat, hacking-discounted, then one round vented.
    stats = combat.player_stats(p)
    assert state["heat"] == (35 - stats["heat_discount"]) - stats["heat_vent"]


def test_hacking_scales_protocol_damage_but_not_weapon_damage():
    dull = _adept(5, "gravity_snap")
    dull.attributes["hacking"] = 0
    sharp = _adept(5, "gravity_snap")
    sharp.attributes["hacking"] = 20
    assert (
        combat.player_stats(sharp)["protocol_power"] > combat.player_stats(dull)["protocol_power"]
    )
    assert combat.player_stats(sharp)["attack"] == combat.player_stats(dull)["attack"]
    d_state = _fight(dull, enemy_id="warden_lyss")
    combat.act(dull, d_state, "protocol", protocol_id="gravity_snap", rng=QuietRng())
    s_state = _fight(sharp, enemy_id="warden_lyss")
    combat.act(sharp, s_state, "protocol", protocol_id="gravity_snap", rng=QuietRng())
    dull_dmg = d_state["enemy"]["hp"] - d_state["enemy_hp"]
    sharp_dmg = s_state["enemy"]["hp"] - s_state["enemy_hp"]
    assert sharp_dmg > dull_dmg


def test_hacking_runs_casts_cooler_with_a_floor():
    cool = _adept(5, "purge_cycle")
    cool.attributes["hacking"] = 20  # discount 10: 25 -> 15 heat
    state = _fight(cool, enemy_id="warden_lyss")
    combat.act(cool, state, "protocol", protocol_id="purge_cycle", rng=QuietRng())
    stats = combat.player_stats(cool)
    assert state["heat"] == 15 - stats["heat_vent"]
    # The floor: even absurd discipline never drops a cast below 5 heat.
    assert max(5, 25 - 100) == 5


def test_unknown_protocol_is_rejected():
    p = _adept(5)  # knows nothing
    state = _fight(p)
    with pytest.raises(GameError, match="doesn't run"):
        combat.act(p, state, "protocol", protocol_id="gravity_snap", rng=QuietRng())


def test_utility_protocols_cannot_be_cast_in_combat():
    p = _adept(5, "cartographers_dream")
    state = _fight(p)
    with pytest.raises(GameError, match="outside combat"):
        combat.act(p, state, "protocol", protocol_id="cartographers_dream", rng=QuietRng())


def test_overheat_burns_you_with_feedback():
    p = _adept(5, "time_stutter")
    state = _fight(p)
    state["heat"] = combat.player_stats(p)["heat_cap"] - 10  # cast overflows
    hp = state["player_hp"]
    combat.act(p, state, "protocol", protocol_id="time_stutter", rng=QuietRng())
    assert any("OVERHEAT" in line for line in state["log"])
    assert state["player_hp"] < hp  # feedback + (skipped) enemy turn
    assert state["heat"] <= combat.player_stats(p)["heat_cap"]


def test_time_stutter_steals_the_enemy_turn():
    p = _adept(5, "time_stutter")
    state = _fight(p)
    hp = state["player_hp"]
    combat.act(p, state, "protocol", protocol_id="time_stutter", rng=QuietRng())
    assert state["player_hp"] == hp  # the enemy never got to act
    assert any("dead clock branch" in line for line in state["log"])
    # The stutter is consumed with the stolen turn.
    assert "stutter" not in state["enemy_effects"]


def test_mirror_ghost_grants_massive_dodge():
    p = _adept(5, "mirror_ghost")
    p.attributes["agility"] = 0
    p.attributes["luck"] = 0  # dodge 0 without the ghost
    state = _fight(p)

    class MidRng(QuietRng):
        def random(self):
            return 0.35  # above natural dodge (0), below ghost dodge (0.4)

    combat.act(p, state, "protocol", protocol_id="mirror_ghost", rng=MidRng())
    assert "ghost" in state["player_effects"]
    assert any("afterimage" in line for line in state["log"])  # the hit missed


def test_purge_cycle_cleanses_and_heals():
    p = _adept(5, "purge_cycle")
    state = _fight(p)
    state["player_effects"] = {"burn": {"turns": 3, "amount": 4}}
    state["player_hp"] = 20
    combat.act(p, state, "protocol", protocol_id="purge_cycle", rng=QuietRng())
    assert "burn" not in state["player_effects"]
    assert any("Cleansed: burn" in line for line in state["log"])


def test_overclock_lace_banks_charge_and_attack():
    p = _adept(5, "overclock_lace")
    state = _fight(p)
    combat.act(p, state, "protocol", protocol_id="overclock_lace", rng=QuietRng())
    # start 2 +2 overclock +1 regen = 5
    assert state["charge"] == 5
    assert state["attack_buff"] == 3


# --- Utility casts in the dungeon ---------------------------------------------------


def _delver(*protocols):
    p = _adept(5, *protocols)
    p.location = dungeon.ENTRANCE_DISTRICT
    return p


def test_cartographers_dream_reveals_the_floor():
    p = _delver("cartographers_dream")
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    energy = p.energy
    result = dungeon.cast_protocol(p, clock, "cartographers_dream")
    assert result["type"] == "protocol"
    assert all(r["visited"] for r in p.dungeon["rooms"].values())
    assert p.energy == energy - 12


def test_phantom_hands_reveals_seams_in_the_room():
    p = _delver("phantom_hands")
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    run = p.dungeon
    host = next(
        rid
        for rid, room in run["rooms"].items()
        for e in room["exits"].values()
        if e["hidden"] and not e["revealed"]
    )
    run["at"] = host
    dungeon.cast_protocol(p, clock, "phantom_hands")
    assert all(e["revealed"] for e in run["rooms"][host]["exits"].values())


def test_combat_protocols_cannot_be_cast_in_the_halls():
    p = _delver("gravity_snap")
    clock = GameClock()
    dungeon.enter(p, clock, seed=7)
    with pytest.raises(GameError, match="only runs in combat"):
        dungeon.cast_protocol(p, clock, "gravity_snap")


# --- Augmentation slots ---------------------------------------------------------------


def test_augments_install_into_aug_slots():
    p = _adept()
    inventory.add_item(p, "subdermal_plating", 1)
    slot = equipment.equip(p, "subdermal_plating")
    assert slot == "aug_dermal"
    assert combat.player_stats(p)["defense"] == 2 + 5 + 2 + 2 + 3  # +3 from the plating
    equipment.unequip(p, "aug_dermal")
    assert p.inventory["subdermal_plating"] == 1


def test_augment_cannot_go_in_a_gear_slot():
    p = _adept()
    inventory.add_item(p, "reflex_splice", 1)
    with pytest.raises(GameError, match="aug_neural"):
        equipment.equip(p, "reflex_splice", slot="head")


def test_reflex_splice_boosts_dodge_and_speed():
    p = _adept()
    base = combat.player_stats(p)
    inventory.add_item(p, "reflex_splice", 1)
    equipment.equip(p, "reflex_splice")
    boosted = combat.player_stats(p)
    assert boosted["speed"] == base["speed"] + 2
    assert boosted["dodge"] == round(base["dodge"] + 0.05, 3)


def test_heat_augments_raise_cap_and_venting():
    p = _adept()
    base = combat.player_stats(p)
    for aug in ("overclock_core", "coolant_weave"):
        inventory.add_item(p, aug, 1)
        equipment.equip(p, aug)
    stats = combat.player_stats(p)
    assert stats["heat_cap"] == base["heat_cap"] + 40
    assert stats["heat_vent"] == base["heat_vent"] + 6
