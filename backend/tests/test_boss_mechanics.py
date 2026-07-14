"""Boss mechanics: telegraphed signatures, phases, element shifts, statuses."""

from game import combat
from game.player import Player


def _player(level=5):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.combat_level = level
    return p


class QuietRng:
    """No crits/variance; never passes chance rolls; picks first choice."""

    def uniform(self, a, b):
        return 1.0

    def random(self):
        return 0.99

    def choice(self, seq):
        return seq[0]


class EagerRng(QuietRng):
    """Passes inflict rolls without critting or dodging."""

    def random(self):
        # Below inflict chances (0.30/0.35); above crit for the levels used
        # here (≤0.18 with speed+luck) and above default dodge (~0.10).
        return 0.2


def _pass_turns(player, state, n):
    """Burn turns with guard (keeps the player alive and doesn't end fights)."""
    for _ in range(n):
        if state["over"]:
            return
        combat.act(player, state, "guard", rng=QuietRng())


# --- Telegraph → unleash -----------------------------------------------------


def test_boss_telegraphs_then_unleashes():
    p = _player(8)
    state = combat.start(p, "chrome_contessa", 3, 400)
    # Cadence is every 4 turns: turns 1-3 normal, turn 4 telegraph.
    _pass_turns(p, state, 3)
    assert state["charging"] is None
    combat.act(p, state, "guard", rng=QuietRng())  # turn 4: telegraph
    assert state["charging"] is not None
    assert any("curtsy" in line.lower() for line in state["log"])
    hp_before = state["player_hp"]
    combat.act(p, state, "attack", rng=QuietRng())  # turn 5: unleash
    assert state["charging"] is None
    assert state["player_hp"] < hp_before
    assert any("unleashes Curtsy of Blades" in line for line in state["log"])


def test_guarding_a_telegraphed_hit_is_much_lighter():
    def run(guard):
        p = _player(8)
        state = combat.start(p, "chrome_contessa", 3, 400)
        _pass_turns(p, state, 4)  # through the telegraph on turn 4
        hp_before = state["player_hp"]
        combat.act(p, state, "guard" if guard else "attack", rng=QuietRng())
        return hp_before - state["player_hp"]

    guarded, unguarded = run(True), run(False)
    assert guarded < unguarded
    # Telegraph guard divides by 3 (vs unguarded full hit).
    assert guarded <= unguarded // 2


# --- Phases -------------------------------------------------------------------


def test_contessa_sheds_armor_at_half_hp():
    p = _player(8)
    state = combat.start(p, "chrome_contessa", 3, 400)
    atk_before = state["enemy"]["attack"]
    def_before = state["enemy"]["defense"]
    state["enemy_hp"] = int(state["enemy"]["hp"] * 0.4)  # below the 50% line
    combat.act(p, state, "guard", rng=QuietRng())
    assert state["phase"] == 1
    assert state["enemy"]["attack"] > atk_before
    assert state["enemy"]["defense"] < def_before
    assert any("sheds her gown-armor" in line for line in state["log"])


def test_phase_triggers_only_once():
    p = _player(8)
    state = combat.start(p, "chrome_contessa", 3, 400)
    state["enemy_hp"] = int(state["enemy"]["hp"] * 0.4)
    combat.act(p, state, "guard", rng=QuietRng())
    atk_after_phase = state["enemy"]["attack"]
    combat.act(p, state, "guard", rng=QuietRng())
    assert state["phase"] == 1
    assert state["enemy"]["attack"] == atk_after_phase


def test_seraph_shifts_element_at_half_hp():
    p = _player(10)
    state = combat.start(p, "neon_seraph", 6, 500)
    assert state["enemy"]["element"] == "voltaic"
    state["enemy_hp"] = int(state["enemy"]["hp"] * 0.45)
    combat.act(p, state, "guard", rng=QuietRng())
    assert state["enemy"]["element"] == "psionic"


def test_empress_has_two_phases():
    p = _player(12)
    state = combat.start(p, "substrate_empress", 9, 600)
    state["enemy_hp"] = int(state["enemy"]["hp"] * 0.30)  # past both lines
    combat.act(p, state, "guard", rng=QuietRng())
    assert state["phase"] == 2


# --- Status effects -----------------------------------------------------------


def test_signature_inflicts_status():
    p = _player(8)
    state = combat.start(p, "warden_lyss", 1, 400)
    _pass_turns(p, state, 4)  # telegraph on 4
    combat.act(p, state, "guard", rng=QuietRng())  # unleash + slow
    assert "slow" in state["player_effects"]


def test_slow_blocks_charge_regen():
    p = _player(8)
    state = combat.start(p, "holo_siren", 1, 400)
    state["player_effects"]["slow"] = {"turns": 2, "amount": 0}
    charge_before = state["charge"]
    combat.act(p, state, "attack", rng=QuietRng())
    assert state["charge"] == charge_before  # no end-of-turn regen while slowed


def test_charm_halves_outgoing_damage():
    def hit(charmed):
        p = _player(8)
        state = combat.start(p, "razor_doll", 4, 400)
        if charmed:
            state["player_effects"]["charm"] = {"turns": 2, "amount": 0}
        hp_before = state["enemy_hp"]
        combat.act(p, state, "attack", rng=QuietRng())
        return hp_before - state["enemy_hp"]

    assert hit(True) < hit(False)


def test_corrode_softens_the_enemy():
    def hit(corroded):
        p = _player(8)
        state = combat.start(p, "razor_doll", 4, 400)
        if corroded:
            state["enemy_effects"]["corrode"] = {"turns": 3, "amount": 0}
        hp_before = state["enemy_hp"]
        combat.act(p, state, "attack", rng=QuietRng())
        return hp_before - state["enemy_hp"]

    assert hit(True) > hit(False)


def test_player_skill_can_inflict_burn():
    p = _player(8)  # flare_burst unlocked at 2
    state = combat.start(p, "razor_doll", 4, 400)
    combat.act(p, state, "skill", skill_id="flare_burst", rng=EagerRng())
    assert "burn" in state["enemy_effects"]


def test_burn_ticks_and_expires():
    p = _player(8)
    state = combat.start(p, "razor_doll", 4, 400)
    state["enemy_effects"]["burn"] = {"turns": 2, "amount": 5}
    hp_before = state["enemy_hp"]
    combat.act(p, state, "guard", rng=QuietRng())  # tick 1
    dealt_by_burn = hp_before - state["enemy_hp"]
    assert dealt_by_burn >= 5  # burn damage landed (guard deals none itself)
    combat.act(p, state, "guard", rng=QuietRng())  # tick 2 -> expires
    assert "burn" not in state["enemy_effects"]


def test_burn_can_finish_an_enemy():
    p = _player(8)
    state = combat.start(p, "holo_siren", 1, 400)
    state["enemy_effects"]["burn"] = {"turns": 3, "amount": 5}
    state["enemy_hp"] = 3  # burn tick will kill between turns
    combat.act(p, state, "guard", rng=QuietRng())
    assert state["over"] is True
    assert state["victory"] is True


def test_regular_enemies_have_no_telegraphs():
    p = _player(8)
    state = combat.start(p, "holo_siren", 1, 400)
    _pass_turns(p, state, 8)
    assert state["charging"] is None


# --- Sanity: mechanics data is well-formed -------------------------------------


def test_all_mechanics_reference_valid_data():
    from game import data

    elements = data.load("elements")
    for enemy in data.load("enemies").values():
        mech = enemy.get("mechanics")
        if not mech:
            continue
        for move in mech.get("moves", []):
            assert move["power"] > 1.0
            assert move["every_n_turns"] >= 2
            assert move["telegraph"]
            if move.get("inflicts"):
                assert move["inflicts"]["effect"] in ("burn", "slow", "charm", "corrode")
        for phase in mech.get("phases", []):
            assert 0 < phase["hp_below"] < 1
            assert phase["text"]
            if phase.get("element"):
                assert phase["element"] in elements
