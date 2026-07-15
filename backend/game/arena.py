"""The Pit — an unlicensed arena under the Docking Quarter. (data/arena.json)

A pure win ladder: losses cost nothing and don't advance it. Every 10th WIN is
a championship bout against a named champion; the first four titles pay a
purse, a unique prize, and real street cred, and the deepest two champions are
the hardest fights in the game — harder than anything under floor ten. Past
the fourth title, every 10th win is an Apex rematch (cred and purse only).

Regular bouts pay no XP, no credits, no drops (combat's arena flag handles
that) — one point of cred per win. The Pit pays in reputation.
"""

import random as _random

from game import combat, data, inventory
from game.errors import GameError

# Reputation thresholds -> how the city knows you.
CRED_STAGES = [
    (0, "Unknown"),
    (10, "Known Face"),
    (40, "Name in the Grid"),
    (100, "Undercard Legend"),
    (200, "Crowd's Own"),
]


def cred_stage(cred):
    label = CRED_STAGES[0][1]
    for threshold, name in CRED_STAGES:
        if cred >= threshold:
            label = name
    return label


def _config():
    return data.load("arena")


def _bracket(wins):
    for bracket in _config()["brackets"]:
        if bracket["max_wins"] is None or wins <= bracket["max_wins"]:
            return bracket
    return _config()["brackets"][-1]


def _championship_for(fight_number):
    """The championship spec for this fight number (None if it's a regular
    bout). Numbers past the listed titles fall through to the Apex rematch."""
    if fight_number % 10 != 0:
        return None
    spec = _config()["championships"].get(str(fight_number))
    return spec if spec is not None else _config()["rematch"]


def next_bout(player):
    """Preview the next fight on the card (deterministic per ladder position)."""
    number = player.arena_wins + 1
    champ = _championship_for(number)
    if champ:
        enemy = data.load("enemies")[champ["enemy"]]
        return {
            "number": number,
            "championship": True,
            "title": champ["title"],
            "enemy": {"id": enemy["id"], "name": enemy["name"], "element": enemy["element"]},
        }
    bracket = _bracket(player.arena_wins)
    pool = sorted(
        eid
        for eid, e in data.load("enemies").items()
        if e["role"] == "normal" and e["tier"] == bracket["pool_tier"]
    )
    rng = _random.Random(f"pit:{player.arena_wins}")
    enemy = data.load("enemies")[rng.choice(pool)]
    return {
        "number": number,
        "championship": False,
        "title": None,
        "enemy": {"id": enemy["id"], "name": enemy["name"], "element": enemy["element"]},
    }


def start_fight(player, clock):
    """Step into the Pit: full HP, no companion (no seconds), arena rules."""
    cfg = _config()
    if player.location != cfg["district"]:
        raise GameError("The Pit is under the docks — Docking Quarter only.")
    if player.combat.get("active"):
        raise GameError("You're already in a fight.")
    if player.dungeon.get("active"):
        raise GameError("The Pit doesn't book fighters mid-delve.")
    if player.energy < cfg["energy"]:
        raise GameError("The crowd can smell exhaustion — rest first.")

    bout = next_bout(player)
    player.energy -= cfg["energy"]
    clock.advance(cfg["minutes"])
    # Champions fight at their tuned base stats; ladder bouts scale by bracket.
    floor = 1 if bout["championship"] else _bracket(player.arena_wins)["scale_floor"]
    max_hp = combat.player_stats(player)["max_hp"]
    player.combat = combat.start(player, bout["enemy"]["id"], floor, max_hp, arena=True)
    if bout["championship"]:
        player.combat["log"].insert(
            0, f"CHAMPIONSHIP — {bout['title']}. The Pit goes quiet, then very loud."
        )
    return bout


def finish_fight(player):
    """Fold a finished Pit bout back into the ladder. Returns the outcome."""
    state = player.combat
    if not state.get("over"):
        raise GameError("The fight isn't over.")
    if not state.get("arena"):
        raise GameError("That wasn't a Pit bout.")

    cfg = _config()
    number = player.arena_wins + 1
    champ = _championship_for(number)
    player.combat = {}

    if state.get("fled"):
        return {"result": "fled", "arena": True, "fight": number, "wins": player.arena_wins}
    if not state["victory"]:
        # No spoils lost either — you just didn't climb.
        return {"result": "defeat", "arena": True, "fight": number, "wins": player.arena_wins}

    player.arena_wins = number
    cred = cfg["win_cred"]
    outcome = {"result": "victory", "arena": True, "fight": number, "wins": number}
    if champ:
        cred += champ["cred"]
        player.credits += champ["purse"]
        outcome["championship"] = {
            "title": champ["title"],
            "cred": champ["cred"],
            "purse": champ["purse"],
        }
        if champ.get("prize"):
            inventory.add_item(player, champ["prize"], 1)
            outcome["championship"]["prize"] = inventory.get_item(champ["prize"])["name"]
    player.street_cred += cred
    outcome["cred_gained"] = cred
    outcome["street_cred"] = player.street_cred
    return outcome


def view(player):
    """The Pit's card, record, and standing for the API."""
    cfg = _config()
    return {
        "name": cfg["name"],
        "district": cfg["district"],
        "blurb": cfg["blurb"],
        "energy": cfg["energy"],
        "minutes": cfg["minutes"],
        "wins": player.arena_wins,
        "titles": min(player.arena_wins // 10, len(cfg["championships"])),
        "street_cred": player.street_cred,
        "cred_stage": cred_stage(player.street_cred),
        "next": next_bout(player),
    }
