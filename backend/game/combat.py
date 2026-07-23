"""JRPG turn-based combat. (Milestone 5)

Server-authoritative battle state lives on the player (``player.combat``) as a
JSON-able dict, so a fight survives page reloads. Player combat stats derive
from the persistent combat level plus attributes; elemental multipliers come
from data/elements.json (1.5x hitting a weakness, 0.5x when resisted); enemy
stats are scaled by floor and by the tunable difficulty table.

Actions: attack, skill (charge-cost elemental strikes), guard (halves the next
hit, banks +1 charge), item (food heals HP in combat), flee (never from bosses).
"""

import random as _random

from game import data, equipment, house, inventory, traits, university
from game.errors import GameError

CHARGE_START = 2
CHARGE_MAX = 5
CHARGE_PER_TURN = 1
CRIT_CHANCE = 0.10  # baseline (companions; fallback when no speed is known)
CRIT_MULT = 1.5
FLEE_CHANCE = 0.6
BASIC_POWER = 1.0
ENEMY_SKILL_CHANCE = 0.3
ENEMY_SKILL_POWER = 1.4

# Crit scales with speed (and a little luck); dodge with agility (and a little
# luck). Both capped so maxed builds stay beatable/hittable.
CRIT_BASE = 0.05
CRIT_PER_SPEED = 0.005
CRIT_PER_LUCK = 0.004
CRIT_CAP = 0.35
DODGE_PER_AGILITY = 0.015
DODGE_PER_LUCK = 0.004
DODGE_CAP = 0.30
FLEE_PER_LUCK = 0.02
FLEE_CAP = 0.9
DROP_PER_LUCK = 0.03  # +3% relative drop chance per luck point

# Wetware protocols: reality-bending code cast from your neural lace. Casting
# builds HEAT; heat vents a little each round. Pushing past capacity fires the
# cast anyway but burns you with feedback.
HEAT_CAP = 100
HEAT_VENT = 8  # shed per round
OVERHEAT_FEEDBACK = 0.12  # of max HP, when a cast overflows the cap
GHOST_DODGE_CAP = 0.6  # dodge ceiling with Mirror Ghost up


def crit_chance(speed, luck=0):
    return min(CRIT_CAP, CRIT_BASE + speed * CRIT_PER_SPEED + luck * CRIT_PER_LUCK)


def dodge_chance(agility, luck=0):
    return min(DODGE_CAP, agility * DODGE_PER_AGILITY + luck * DODGE_PER_LUCK)


# Status effects (registry: data/statuses.json). Mechanics live here; names,
# hints, and chip colors live in the registry so the UI stays data-driven.
# On YOU: burn (DoT), slow (no charge regen), charm (damage halved), corrode
# (defense halved), smitten (charm + you may lose your turn admiring them),
# marked (+25% damage taken), weak_knees (no dodge, crits falter), static_cling
# (-1 charge/turn), drained (DoT that heals the enemy), ghost (dodge boost).
# On THEM: burn, corrode, stutter/stagger (lose a turn), shock (-25% attack),
# entranced (basic attacks only — no telegraphs, no charged strikes).
ENEMY_STATUSES = ("burn", "corrode")
SKILL_INFLICT_CHANCE = 0.30  # player skills (element-mapped fallback)
ENEMY_SKILL_INFLICT_CHANCE = 0.35  # enemy charged strikes
DEFAULT_BURN = 4
SMITTEN_SLIP_CHANCE = 0.35  # chance an offensive action is lost to admiring
MARKED_MULT = 1.25  # damage taken while marked
SHOCK_MULT = 0.75  # enemy attack while shocked
STAGGER_MINIBOSS_RESIST = 0.5  # bosses are outright immune
# Guarding a telegraphed signature move cuts it to a third (regular guard: half).
TELEGRAPH_GUARD_DIVISOR = 3


def element_multiplier(attack_elem, defend_elem):
    if not attack_elem or not defend_elem:
        return 1.0
    elements = data.load("elements")
    if defend_elem in elements.get(attack_elem, {}).get("strong_vs", []):
        return 1.5
    if attack_elem in elements.get(defend_elem, {}).get("strong_vs", []):
        return 0.5
    return 1.0


def player_stats(player):
    """Combat stats derived from persistent level + attributes + equipment."""
    level = player.combat_level
    courage = player.attributes.get("courage", 5)
    wit = player.attributes.get("wit", 5)
    agility = player.attributes.get("agility", 5)
    # Lyceum's The Long Tail (PRB 301) tips the rare outcomes — crits, dodges,
    # drops — as does a home the sea keeps lucky (the Salt Wren houseboat).
    luck = (
        player.attributes.get("luck", 5)
        + university.bonus(player, "luck_bonus")
        + house.bonus(player, "luck_bonus")
    )
    hacking = player.attributes.get("hacking", 5)
    eq = equipment.bonuses(player)
    speed = 5 + level + wit + eq["speed"]
    # Species traits (game/traits.py): Built For It, Escape Artist, Native Signal.
    # The Founder's Nerve (NRV 301) multiplies here too.
    hp_mult = traits.effect(player, "max_hp_mult", 1.0) * university.mult(player, "max_hp_mult")
    return {
        "level": level,
        "max_hp": round((30 + level * 10 + courage * 2 + eq["max_hp"]) * hp_mult),
        "attack": 6 + level * 2 + courage + eq["attack"],
        "defense": 2 + level + wit // 2 + agility // 2 + eq["defense"],
        "speed": speed,
        "crit": round(crit_chance(speed, luck), 3),
        "dodge": round(
            min(0.5, dodge_chance(agility, luck) + eq["dodge"] + traits.effect(player, "dodge", 0)),
            3,
        ),
        "luck": luck,
        # Hacking is the casting stat: strike protocols swing with lace power
        # (not your weapon arm), and a disciplined lace runs cooler per cast.
        # Ghost in the Citadel (SYS 301) / Root Access (SYS 401) add to both.
        "protocol_power": 6
        + level * 2
        + hacking * 2
        + university.bonus(player, "protocol_power_bonus"),
        "heat_discount": hacking // 2,
        "heat_cap": HEAT_CAP
        + eq["heat_cap"]
        + traits.effect(player, "heat_cap", 0)
        + university.bonus(player, "heat_cap"),
        "heat_vent": HEAT_VENT + eq["heat_vent"],
    }


def _best_element_against(defend_elem):
    """The element the defender is weak to (for the Prisma Gem's auto-target)."""
    for elem, spec in data.load("elements").items():
        if defend_elem in spec.get("strong_vs", []):
            return elem
    return "kinetic"


def attack_element(player, enemy_element):
    """What element your basic attack carries, given your weapon's gems."""
    eq = equipment.bonuses(player)
    if eq["auto_weakness"]:
        return _best_element_against(enemy_element)
    return eq["weapon_element"] or "kinetic"


def incoming_resist(player, attack_elem):
    """0.5 if your armor gems resist the incoming element, else 1.0."""
    eq = equipment.bonuses(player)
    if eq["resist_all"] or attack_elem in eq["resists"]:
        return 0.5
    return 1.0


def xp_to_next(level):
    return 20 + (level - 1) * 15


def grant_xp(player, xp):
    """Add XP, applying any level-ups. Returns the number of levels gained."""
    player.combat_xp += xp
    ups = 0
    while player.combat_xp >= xp_to_next(player.combat_level):
        player.combat_xp -= xp_to_next(player.combat_level)
        player.combat_level += 1
        ups += 1
    return ups


def unlocked_skills(level):
    return {
        sid: skill for sid, skill in data.load("skills").items() if level >= skill["unlock_level"]
    }


def scaled_enemy(enemy_id, floor, difficulty):
    """An enemy's stats scaled by floor depth and the difficulty table."""
    base = data.load("enemies")[enemy_id]
    diff = data.load("difficulty")[difficulty]
    scale = 1 + 0.08 * (floor - 1)
    return {
        **base,
        "hp": round(base["hp"] * scale * diff["enemy_hp"]),
        "attack": round(base["attack"] * scale * diff["enemy_attack"]),
        "defense": round(base["defense"] * scale),
    }


def _damage(attack, power, defense, elem_mult, rng, crit=CRIT_CHANCE):
    variance = rng.uniform(0.9, 1.1)
    is_crit = rng.random() < crit
    raw = attack * power * elem_mult * variance * (CRIT_MULT if is_crit else 1.0)
    return max(1, round(raw - defense * 0.5)), is_crit


def start(player, enemy_id, floor, player_hp, attack_buff=0, companion=None, arena=False):
    """Begin a battle. Returns the new combat state dict."""
    enemy = scaled_enemy(enemy_id, floor, player.difficulty)
    stats = player_stats(player)
    eq = equipment.bonuses(player)
    charge_max = CHARGE_MAX + eq["charge_max"]
    return {
        "active": True,
        "arena": arena,  # Pit bouts: no XP, no credits, no drops — cred only
        "companion": dict(companion) if companion else None,
        "enemy": enemy,
        "enemy_hp": enemy["hp"],
        "player_hp": min(player_hp, stats["max_hp"]),
        "charge": min(charge_max, CHARGE_START + eq["charge_start"]),
        "charge_max": charge_max,
        "guarding": False,
        "attack_buff": attack_buff,
        "heat": 0,  # wetware protocol heat
        "turn": 1,
        "log": [f"{enemy['name']} bars your way."],
        "player_effects": {},  # {status: {turns, amount}}
        "enemy_effects": {},
        "charging": None,  # a telegraphed move waiting to be unleashed
        "phase": 0,  # count of boss phases already triggered
        "over": False,
        "victory": False,
        "fled": False,
        "rewards": None,
    }


def _status_for(element):
    return data.load("elements").get(element, {}).get("status")


def _resisted_turns(player, turns):
    """Patient Metabolism: statuses on the player burn out a turn sooner."""
    return max(1, turns - traits.effect(player, "status_turns_resist", 0))


def _inflict(effects, effect, turns, amount=0):
    if effect == "smitten":
        effects.pop("charm", None)  # smitten supersedes charm, never stacks with it
    effects[effect] = {
        "turns": turns,
        "amount": amount or (DEFAULT_BURN if effect == "burn" else 0),
    }


def _inflict_enemy(state, effect, turns, rng, amount=0):
    """Land a status on the enemy, respecting stagger immunities. Returns
    whether it stuck (and logs the resist when it doesn't)."""
    role = state["enemy"].get("role", "normal")
    if effect == "stagger":
        if role == "boss":
            state["log"].append(f"{state['enemy']['name']} doesn't even wobble.")
            return False
        if role == "miniboss" and rng.random() < STAGGER_MINIBOSS_RESIST:
            state["log"].append(f"{state['enemy']['name']} rides the hit and keeps their feet.")
            return False
    _inflict(state["enemy_effects"], effect, turns, amount)
    return True


def _check_phases(state):
    """Trigger any boss phases the enemy's HP has fallen past (each fires once)."""
    mech = state["enemy"].get("mechanics") or {}
    phases = mech.get("phases", [])
    max_hp = state["enemy"]["hp"]
    while state["phase"] < len(phases):
        phase = phases[state["phase"]]
        if state["enemy_hp"] > max_hp * phase["hp_below"]:
            break
        enemy = state["enemy"]
        enemy["attack"] = round(enemy["attack"] * phase.get("attack_mult", 1.0))
        enemy["defense"] = round(enemy["defense"] * phase.get("defense_mult", 1.0))
        if phase.get("element"):
            enemy["element"] = phase["element"]
        state["log"].append(phase["text"])
        state["phase"] += 1


def _tick_effects(state):
    """End-of-round: apply burn/drain damage and count every effect down."""
    log = state["log"]
    pe, ee = state["player_effects"], state["enemy_effects"]
    if "burn" in pe:
        dmg = pe["burn"]["amount"]
        state["player_hp"] = max(0, state["player_hp"] - dmg)
        log.append(f"Burn sears you — {dmg} damage.")
    if "drained" in pe:
        # Vampiric: what she sips, she keeps. The sip alone can't finish you.
        sip = min(pe["drained"]["amount"], state["player_hp"] - 1)
        if sip > 0:
            state["player_hp"] -= sip
            state["enemy_hp"] = min(state["enemy"]["hp"], state["enemy_hp"] + sip)
            log.append(f"{state['enemy']['name']} sips your warmth and sighs — {sip} HP, hers now.")
    if "burn" in ee:
        dmg = ee["burn"]["amount"]
        state["enemy_hp"] = max(0, state["enemy_hp"] - dmg)
        log.append(f"{state['enemy']['name']} burns — {dmg} damage.")
    for effects in (pe, ee):
        for name in list(effects):
            effects[name]["turns"] -= 1
            if effects[name]["turns"] <= 0:
                del effects[name]


def _companion_turn(player, state, rng):
    """The companion acts once per round, by role. Auto-piloted."""
    comp = state.get("companion")
    if not comp or comp["down"] or state["over"] or state["enemy_hp"] <= 0:
        return
    enemy = state["enemy"]
    log = state["log"]
    enemy_defense = enemy["defense"] * (0.5 if "corrode" in state["enemy_effects"] else 1.0)
    pstats = player_stats(player)

    def strike(power, note=""):
        mult = element_multiplier(comp["element"], enemy["element"])
        dmg, _ = _damage(comp["attack"], power, enemy_defense, mult, rng)
        state["enemy_hp"] = max(0, state["enemy_hp"] - dmg)
        extra = " It hits a weakness!" if mult > 1 else ""
        log.append(f"{comp['name']} strikes — {dmg} damage.{extra}{note}")

    role = comp["role"]
    if role == "healer":
        if state["player_hp"] < pstats["max_hp"] * 0.6:
            heal = 12 + pstats["level"] * 2
            state["player_hp"] = min(pstats["max_hp"], state["player_hp"] + heal)
            log.append(f"{comp['name']} tends to you — +{heal} HP.")
            if state["player_effects"]:
                cured = next(iter(state["player_effects"]))
                del state["player_effects"][cured]
                log.append(f"{comp['name']} clears the {cured} from your system.")
        else:
            strike(0.9)
    elif role == "dps":
        strike(1.3)
    elif role == "support":
        state["charge"] = min(state.get("charge_max", CHARGE_MAX), state["charge"] + 1)
        strike(0.7, " Their rhythm feeds your charge (+1).")
    elif role == "rogue":
        strike(1.1)
    else:  # tank
        strike(0.8)


def _enemy_turn(player, state, pstats, rng):
    enemy = state["enemy"]
    log = state["log"]
    pe = state["player_effects"]
    # Corrode on you halves your effective defense.
    defense = pstats["defense"] * (0.5 if "corrode" in pe else 1.0)
    # Armor gems (or a prisma) blunt the enemy's element.
    resist = incoming_resist(player, enemy["element"])
    # Enemies crit off their own speed; your dodge comes from agility + luck,
    # plus Mirror Ghost's echo while it lasts.
    enemy_crit = crit_chance(enemy.get("speed", 5))
    ghost = pe.get("ghost", {}).get("amount", 0)
    # Weak knees: no dancing out of anything. Shock: their arm's gone numb.
    dodge = 0 if "weak_knees" in pe else min(GHOST_DODGE_CAP, pstats["dodge"] + ghost)
    atk = round(enemy["attack"] * (SHOCK_MULT if "shock" in state["enemy_effects"] else 1.0))
    marked = MARKED_MULT if "marked" in pe else 1.0

    if "stutter" in state["enemy_effects"]:
        log.append(f"{enemy['name']} hangs mid-motion, caught in a dead clock branch.")
        return
    if "stagger" in state["enemy_effects"]:
        log.append(f"{enemy['name']} is still finding their feet after that hip check.")
        return
    entranced = "entranced" in state["enemy_effects"]

    if state.get("charging"):
        # Unleash the telegraphed signature move. Signatures can't be dodged —
        # reading the telegraph and guarding is the counter.
        move = state["charging"]
        state["charging"] = None
        dmg, _crit = _damage(atk, move["power"], defense, resist, rng, crit=enemy_crit)
        dmg = round(dmg * marked)
        if state["guarding"]:
            # Warforms (Built For It) brace harder than the standard divisor.
            divisor = traits.effect(player, "telegraph_guard_divisor", TELEGRAPH_GUARD_DIVISOR)
            dmg = max(1, dmg // divisor)
            state["guarding"] = False
            log.append(f"You read it perfectly and brace through {move['name']}.")
        state["player_hp"] = max(0, state["player_hp"] - dmg)
        log.append(f"{enemy['name']} unleashes {move['name']} — {dmg} damage!")
        inflict = move.get("inflicts")
        if inflict and state["player_hp"] > 0:
            turns = _resisted_turns(player, inflict["turns"])
            _inflict(pe, inflict["effect"], turns, inflict.get("amount", 0))
            log.append(f"You're afflicted: {inflict['effect']}!")
    else:
        moves = (enemy.get("mechanics") or {}).get("moves") or []
        if moves and not entranced and state["turn"] % moves[0].get("every_n_turns", 4) == 0:
            # Telegraph: the boss spends this turn charging — your cue to guard.
            # An entranced boss can't focus enough to wind one up.
            move = rng.choice(moves)
            state["charging"] = move
            log.append(move["telegraph"])
        else:
            use_skill = not moves and not entranced and rng.random() < ENEMY_SKILL_CHANCE
            power = ENEMY_SKILL_POWER if use_skill else BASIC_POWER
            comp = state.get("companion")
            target_comp = False
            if comp and not comp["down"]:
                roll = rng.random()
                target_comp = roll < (0.55 if comp["role"] == "tank" else 0.25)
            if target_comp:
                dmg, crit = _damage(atk, power, comp["defense"], 1.0, rng, crit=enemy_crit)
                comp["hp"] = max(0, comp["hp"] - dmg)
                log.append(f"{enemy['name']} turns on {comp['name']} — {dmg} damage.")
                if comp["hp"] <= 0:
                    comp["down"] = True
                    log.append(f"{comp['name']} goes down! They'll need a rest stop.")
            elif rng.random() < dodge:
                verb = "a charged strike" if use_skill else "the blow"
                log.append(f"You twist aside — {verb} finds nothing but afterimage.")
            else:
                dmg, crit = _damage(atk, power, defense, resist, rng, crit=enemy_crit)
                dmg = round(dmg * marked)
                if state["guarding"]:
                    dmg = max(1, dmg // 2)
                    state["guarding"] = False
                if comp and not comp["down"] and comp["role"] == "tank" and dmg > 2:
                    absorbed = round(dmg * 0.3)
                    comp["hp"] = max(0, comp["hp"] - absorbed)
                    dmg -= absorbed
                    log.append(f"{comp['name']} shoulders {absorbed} of the hit.")
                    if comp["hp"] <= 0:
                        comp["down"] = True
                        log.append(f"{comp['name']} goes down! They'll need a rest stop.")
                state["player_hp"] = max(0, state["player_hp"] - dmg)
                verb = "unleashes a charged strike" if use_skill else "attacks"
                log.append(f"{enemy['name']} {verb} — {dmg} damage{' (crit!)' if crit else ''}.")
                if use_skill and rng.random() < ENEMY_SKILL_INFLICT_CHANCE:
                    status = _status_for(enemy["element"])
                    if status and state["player_hp"] > 0:
                        _inflict(pe, status, _resisted_turns(player, 2))
                        log.append(f"You're afflicted: {status}!")

    if state["player_hp"] <= 0:
        state["over"] = True
        state["victory"] = False
        log.append("You go down. The Substrate spits you back out.")


def roll_drops(enemy, rng, luck=0):
    """Roll the enemy's loot table (data/loot.json). Normals roll by tier with a
    drop chance; minibosses always drop; bosses roll twice, guaranteed — plus a
    slim jackpot roll for the super-rare gems. Luck fattens every roll."""
    tables = data.load("loot")
    role = enemy.get("role", "normal")
    table = tables[role] if role != "normal" else tables["normal"][str(enemy["tier"])]
    fortune = 1 + luck * DROP_PER_LUCK
    drops = []
    for _ in range(table.get("rolls", 1)):
        if rng.random() < min(1.0, table["chance"] * fortune):
            drops.append(rng.choice(table["items"]))
    bonus = table.get("bonus")
    if bonus and rng.random() < min(1.0, bonus["chance"] * fortune):
        drops.append(rng.choice(bonus["items"]))
    return drops


def _win(state, player, rng):
    enemy = state["enemy"]
    state["over"] = True
    state["victory"] = True

    if state.get("arena"):
        # The Pit pays in reputation, not spoils (championship purses are
        # handled by the arena module, not the fight itself).
        state["rewards"] = None
        state["log"].append(f"{enemy['name']} goes down. The crowd decides it loves you.")
        return

    diff = data.load("difficulty")[player.difficulty]
    eq = equipment.bonuses(player)
    comp = state.get("companion")
    rogue_bonus = 1 + comp.get("credit_bonus", 0) if comp and not comp["down"] else 1
    xp = round(enemy["xp"] * diff["xp"] * eq["xp_mult"])
    credits = round(enemy["credits"] * rng.uniform(0.85, 1.15) * eq["credit_mult"] * rogue_bonus)
    ups = grant_xp(player, xp)
    player.credits += credits

    drops = roll_drops(
        enemy,
        rng,
        luck=(
            player.attributes.get("luck", 0)
            + university.bonus(player, "luck_bonus")
            + house.bonus(player, "luck_bonus")
        ),
    )
    for item_id in drops:
        inventory.add_item(player, item_id, 1)
    drop_names = [inventory.get_item(i)["name"] for i in drops]

    state["rewards"] = {"xp": xp, "credits": credits, "level_ups": ups, "drops": drop_names}
    state["log"].append(f"{enemy['name']} falls. +{xp} XP, +{credits} cr.")
    for name in drop_names:
        state["log"].append(f"They drop: {name}.")
    if ups:
        state["log"].append(f"Level up! You're now level {player.combat_level}.")
        # A level-up brings a rush of strength: fully restored.
        state["player_hp"] = player_stats(player)["max_hp"]


def _cast_protocol(player, state, protocol, pstats, enemy_defense, charmed, pcrit, rng):
    """Run a combat protocol: add heat (overflow = feedback damage), then apply
    the effect by kind."""
    log = state["log"]
    heat_cap = pstats["heat_cap"]
    # A practiced hacker runs the same code cooler (never below 5 heat).
    cost = max(5, protocol["heat"] - pstats["heat_discount"])
    state["heat"] += cost
    log.append(f"You run {protocol['name']} — heat {min(state['heat'], heat_cap)}/{heat_cap}.")
    if state["heat"] > heat_cap:
        state["heat"] = heat_cap
        feedback = round(pstats["max_hp"] * OVERHEAT_FEEDBACK)
        state["player_hp"] = max(0, state["player_hp"] - feedback)
        log.append(f"OVERHEAT — feedback arcs through your lace: {feedback} damage.")

    kind = protocol["kind"]
    if kind == "strike":
        mult = element_multiplier(protocol.get("element"), state["enemy"]["element"])
        atk = pstats["protocol_power"] + state.get("attack_buff", 0)
        dmg, crit = _damage(atk, protocol["power"], enemy_defense, mult, rng, crit=pcrit)
        if charmed:
            dmg = max(1, dmg // 2)
        state["enemy_hp"] = max(0, state["enemy_hp"] - dmg)
        note = " It hits a weakness!" if mult > 1 else (" Resisted." if mult < 1 else "")
        log.append(f"{protocol['name']} — {dmg} damage{' (crit!)' if crit else ''}.{note}")
    elif kind == "stutter":
        _inflict(state["enemy_effects"], "stutter", 1)
        log.append(f"{state['enemy']['name']}'s clock forks — and one branch quietly dies.")
    elif kind == "ghost":
        state["player_effects"]["ghost"] = {
            "turns": protocol.get("turns", 2),
            "amount": protocol.get("dodge_bonus", 0.4),
        }
        log.append("A sensory echo peels off you and takes half a step left.")
    elif kind == "purge":
        cleared = list(state["player_effects"])
        state["player_effects"] = {}
        heal = 10 + pstats["level"]
        state["player_hp"] = min(pstats["max_hp"], state["player_hp"] + heal)
        cleared_note = f" Cleansed: {', '.join(cleared)}." if cleared else ""
        log.append(f"Purge Cycle reboots your chemistry — +{heal} HP.{cleared_note}")
    elif kind == "overclock":
        state["charge"] = min(
            state.get("charge_max", CHARGE_MAX), state["charge"] + protocol.get("charge", 2)
        )
        state["attack_buff"] = state.get("attack_buff", 0) + protocol.get("attack_buff", 3)
        log.append("Your lace screams past spec — charge floods in, every edge sharpens.")
    elif kind == "entrance":
        _inflict(state["enemy_effects"], "entranced", protocol.get("turns", 2))
        log.append(
            f"You project {state['enemy']['name']}'s own fantasy back at them. "
            "They forget to be clever."
        )


def act(player, state, action, skill_id=None, item_id=None, rng=None, protocol_id=None):
    """Resolve one player action (and the enemy's answer) in place."""
    rng = rng or _random
    if not state.get("active") or state.get("over"):
        raise GameError("There's no fight to act in.")

    pstats = player_stats(player)
    enemy = state["enemy"]
    state["guarding"] = False
    pe = state["player_effects"]

    # Corrode on the enemy halves their defense; charm (or being smitten)
    # halves your output; weak knees make your crits falter.
    enemy_defense = enemy["defense"] * (0.5 if "corrode" in state["enemy_effects"] else 1.0)
    charmed = "charm" in pe or "smitten" in pe
    pcrit = pstats["crit"] * (0.5 if "weak_knees" in pe else 1.0)

    # Smitten: offensive actions can be lost to a long moment of admiring them.
    if (
        action in ("attack", "skill", "protocol")
        and "smitten" in pe
        and rng.random() < SMITTEN_SLIP_CHANCE
    ):
        state["log"].append(
            f"You raise your hand — and spend the moment watching the light move on "
            f"{enemy['name']} instead."
        )
        action = "__slipped__"

    if action == "__slipped__":
        pass  # your turn, wasted beautifully

    elif action == "attack":
        elem = attack_element(player, enemy["element"])  # weapon gems can change this
        mult = element_multiplier(elem, enemy["element"])
        atk = pstats["attack"] + state.get("attack_buff", 0)
        dmg, crit = _damage(atk, BASIC_POWER, enemy_defense, mult, rng, crit=pcrit)
        if charmed:
            dmg = max(1, dmg // 2)
        state["enemy_hp"] = max(0, state["enemy_hp"] - dmg)
        note = " It hits a weakness!" if mult > 1 else (" Resisted." if mult < 1 else "")
        if charmed:
            note += " (charmed — your heart isn't in it)"
        state["log"].append(f"You attack — {dmg} damage{' (crit!)' if crit else ''}.{note}")

    elif action == "skill":
        skills = unlocked_skills(player.combat_level)
        skill = skills.get(skill_id)
        if skill is None:
            raise GameError("You haven't learned that skill.")
        if state["charge"] < skill["cost"]:
            raise GameError("Not enough charge.")
        state["charge"] -= skill["cost"]
        mult = element_multiplier(skill["element"], enemy["element"])
        atk = pstats["attack"] + state.get("attack_buff", 0)
        dmg, crit = _damage(atk, skill["power"], enemy_defense, mult, rng, crit=pcrit)
        if charmed:
            dmg = max(1, dmg // 2)
        state["enemy_hp"] = max(0, state["enemy_hp"] - dmg)
        note = " It hits a weakness!" if mult > 1 else (" Resisted." if mult < 1 else "")
        if charmed:
            note += " (charmed)"
        state["log"].append(f"{skill['name']} — {dmg} damage{' (crit!)' if crit else ''}.{note}")
        if state["enemy_hp"] > 0:
            spec = skill.get("inflicts")
            if spec:
                # Signature inflicts (the sexy attacks): entrance, stagger, shock.
                if rng.random() < spec["chance"]:
                    if _inflict_enemy(state, spec["effect"], spec["turns"], rng):
                        state["log"].append(f"{enemy['name']} is afflicted: {spec['effect']}!")
            else:
                # Thermal/toxin skills can afflict the enemy (burn / corrode).
                status = _status_for(skill["element"])
                if status in ENEMY_STATUSES and rng.random() < SKILL_INFLICT_CHANCE:
                    _inflict(state["enemy_effects"], status, 3)
                    state["log"].append(f"{enemy['name']} is afflicted: {status}!")

    elif action == "protocol":
        protocol = data.load("protocols").get(protocol_id)
        if protocol is None or protocol_id not in player.protocols:
            raise GameError("Your lace doesn't run that protocol.")
        if protocol["kind"] not in ("strike", "stutter", "ghost", "purge", "overclock", "entrance"):
            raise GameError(f"{protocol['name']} only runs outside combat.")
        _cast_protocol(player, state, protocol, pstats, enemy_defense, charmed, pcrit, rng)

    elif action == "guard":
        state["guarding"] = True
        state["charge"] = min(state.get("charge_max", CHARGE_MAX), state["charge"] + 1)
        state["log"].append("You brace and bank a charge.")

    elif action == "item":
        item = inventory.get_item(item_id)
        if item.get("type") == "booster":
            # Combat-only consumable: charge dump, or a status cleanse.
            inventory.remove_item(player, item_id, 1)
            effects = item.get("effects", {})
            if "cleanse" in effects:
                cleared = [s for s in effects["cleanse"] if pe.pop(s, None)]
                if cleared:
                    state["log"].append(
                        f"{item['name']} — composure restored. Cleansed: {', '.join(cleared)}."
                    )
                else:
                    state["log"].append(f"{item['name']} — bracing, but you were already composed.")
            else:
                gain = effects.get("charge", 0)
                state["charge"] = min(state.get("charge_max", CHARGE_MAX), state["charge"] + gain)
                state["log"].append(f"You slot a {item['name']} — +{gain} charge.")
        else:
            result = inventory.use_item(player, item_id)  # validates + consumes
            heal = result["energy"]
            state["player_hp"] = min(pstats["max_hp"], state["player_hp"] + heal)
            state["log"].append(f"You use {result['item']} — +{heal} HP.")

    elif action == "flee":
        if enemy.get("role") == "boss":
            raise GameError(f"{enemy['name']} won't let you leave.")
        # Escape Artists always find the seam (bosses still corner you, above).
        if traits.effect(player, "flee_always", False) or rng.random() < min(
            FLEE_CAP, FLEE_CHANCE + pstats["luck"] * FLEE_PER_LUCK
        ):
            state["over"] = True
            state["fled"] = True
            state["log"].append("You slip away into the dark.")
            return state
        state["log"].append("You can't find an opening!")

    else:
        raise GameError(f"Unknown combat action: {action!r}")

    if state["player_hp"] <= 0:
        # Overheat feedback can finish you before the enemy even moves.
        state["over"] = True
        state["victory"] = False
        state["log"].append("Your own lace burns you down. The Substrate spits you back out.")
        return state

    if state["enemy_hp"] <= 0:
        _win(state, player, rng)
        return state

    _check_phases(state)
    _companion_turn(player, state, rng)
    if state["enemy_hp"] <= 0:
        _win(state, player, rng)
        return state
    _check_phases(state)
    _enemy_turn(player, state, pstats, rng)
    if not state["over"]:
        _tick_effects(state)
        if state["player_hp"] <= 0:
            state["over"] = True
            state["victory"] = False
            state["log"].append("You go down. The Substrate spits you back out.")
        elif state["enemy_hp"] <= 0:
            # Burn can finish an enemy between turns.
            _win(state, player, rng)
        else:
            if "slow" not in state["player_effects"]:
                state["charge"] = min(
                    state.get("charge_max", CHARGE_MAX), state["charge"] + CHARGE_PER_TURN
                )
            if "static_cling" in state["player_effects"] and state["charge"] > 0:
                state["charge"] -= 1
                state["log"].append(
                    "Static cling grounds a charge through wherever she touched you."
                )
            state["heat"] = max(0, state.get("heat", 0) - pstats["heat_vent"])
            state["turn"] += 1
    return state
