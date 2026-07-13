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

from game import data, inventory
from game.errors import GameError

CHARGE_START = 2
CHARGE_MAX = 5
CHARGE_PER_TURN = 1
CRIT_CHANCE = 0.10
CRIT_MULT = 1.5
FLEE_CHANCE = 0.6
BASIC_POWER = 1.0
ENEMY_SKILL_CHANCE = 0.3
ENEMY_SKILL_POWER = 1.4


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
    """Combat stats derived from persistent level + attributes."""
    level = player.combat_level
    courage = player.attributes.get("courage", 5)
    wit = player.attributes.get("wit", 5)
    return {
        "level": level,
        "max_hp": 30 + level * 10 + courage * 2,
        "attack": 6 + level * 2 + courage,
        "defense": 2 + level + wit // 2,
        "speed": 5 + level + wit,
    }


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


def _damage(attack, power, defense, elem_mult, rng):
    variance = rng.uniform(0.9, 1.1)
    crit = rng.random() < CRIT_CHANCE
    raw = attack * power * elem_mult * variance * (CRIT_MULT if crit else 1.0)
    return max(1, round(raw - defense * 0.5)), crit


def start(player, enemy_id, floor, player_hp, attack_buff=0):
    """Begin a battle. Returns the new combat state dict."""
    enemy = scaled_enemy(enemy_id, floor, player.difficulty)
    stats = player_stats(player)
    return {
        "active": True,
        "enemy": enemy,
        "enemy_hp": enemy["hp"],
        "player_hp": min(player_hp, stats["max_hp"]),
        "charge": CHARGE_START,
        "guarding": False,
        "attack_buff": attack_buff,
        "turn": 1,
        "log": [f"{enemy['name']} bars your way."],
        "over": False,
        "victory": False,
        "fled": False,
        "rewards": None,
    }


def _enemy_turn(state, pstats, rng):
    enemy = state["enemy"]
    use_skill = rng.random() < ENEMY_SKILL_CHANCE
    power = ENEMY_SKILL_POWER if use_skill else BASIC_POWER
    mult = element_multiplier(enemy["element"], None)  # player has no element
    dmg, crit = _damage(enemy["attack"], power, pstats["defense"], mult, rng)
    if state["guarding"]:
        dmg = max(1, dmg // 2)
        state["guarding"] = False
    state["player_hp"] = max(0, state["player_hp"] - dmg)
    verb = "unleashes a charged strike" if use_skill else "attacks"
    state["log"].append(f"{enemy['name']} {verb} — {dmg} damage{' (crit!)' if crit else ''}.")
    if state["player_hp"] <= 0:
        state["over"] = True
        state["victory"] = False
        state["log"].append("You go down. The Substrate spits you back out.")


def roll_drops(enemy, rng):
    """Roll the enemy's loot table (data/loot.json). Normals roll by tier with a
    drop chance; minibosses always drop; bosses roll twice, guaranteed."""
    tables = data.load("loot")
    role = enemy.get("role", "normal")
    table = tables[role] if role != "normal" else tables["normal"][str(enemy["tier"])]
    drops = []
    for _ in range(table.get("rolls", 1)):
        if rng.random() < table["chance"]:
            drops.append(rng.choice(table["items"]))
    return drops


def _win(state, player, rng):
    enemy = state["enemy"]
    diff = data.load("difficulty")[player.difficulty]
    xp = round(enemy["xp"] * diff["xp"])
    credits = round(enemy["credits"] * rng.uniform(0.85, 1.15))
    state["over"] = True
    state["victory"] = True
    ups = grant_xp(player, xp)
    player.credits += credits

    drops = roll_drops(enemy, rng)
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


def act(player, state, action, skill_id=None, item_id=None, rng=None):
    """Resolve one player action (and the enemy's answer) in place."""
    rng = rng or _random
    if not state.get("active") or state.get("over"):
        raise GameError("There's no fight to act in.")

    pstats = player_stats(player)
    enemy = state["enemy"]
    state["guarding"] = False

    if action == "attack":
        mult = element_multiplier("kinetic", enemy["element"])
        atk = pstats["attack"] + state.get("attack_buff", 0)
        dmg, crit = _damage(atk, BASIC_POWER, enemy["defense"], mult, rng)
        state["enemy_hp"] = max(0, state["enemy_hp"] - dmg)
        state["log"].append(f"You attack — {dmg} damage{' (crit!)' if crit else ''}.")

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
        dmg, crit = _damage(atk, skill["power"], enemy["defense"], mult, rng)
        state["enemy_hp"] = max(0, state["enemy_hp"] - dmg)
        note = " It hits a weakness!" if mult > 1 else (" Resisted." if mult < 1 else "")
        state["log"].append(f"{skill['name']} — {dmg} damage{' (crit!)' if crit else ''}.{note}")

    elif action == "guard":
        state["guarding"] = True
        state["charge"] = min(CHARGE_MAX, state["charge"] + 1)
        state["log"].append("You brace and bank a charge.")

    elif action == "item":
        item = inventory.get_item(item_id)
        if item.get("type") == "booster":
            # Combat-only consumable: dumps charge into your systems.
            inventory.remove_item(player, item_id, 1)
            gain = item.get("effects", {}).get("charge", 0)
            state["charge"] = min(CHARGE_MAX, state["charge"] + gain)
            state["log"].append(f"You slot a {item['name']} — +{gain} charge.")
        else:
            result = inventory.use_item(player, item_id)  # validates + consumes
            heal = result["energy"]
            state["player_hp"] = min(pstats["max_hp"], state["player_hp"] + heal)
            state["log"].append(f"You use {result['item']} — +{heal} HP.")

    elif action == "flee":
        if enemy.get("role") == "boss":
            raise GameError(f"{enemy['name']} won't let you leave.")
        if rng.random() < FLEE_CHANCE:
            state["over"] = True
            state["fled"] = True
            state["log"].append("You slip away into the dark.")
            return state
        state["log"].append("You can't find an opening!")

    else:
        raise GameError(f"Unknown combat action: {action!r}")

    if state["enemy_hp"] <= 0:
        _win(state, player, rng)
        return state

    _enemy_turn(state, pstats, rng)
    if not state["over"]:
        state["charge"] = min(CHARGE_MAX, state["charge"] + CHARGE_PER_TURN)
        state["turn"] += 1
    return state
