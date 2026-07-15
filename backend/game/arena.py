"""The Pit — an unlicensed arena, a real venue under the Grid. (data/arena.json)

A pure win ladder: losses cost nothing and don't advance it. Every 10th WIN is
a championship bout against a named champion; the first four titles pay a
purse, a unique prize, and real street cred, and the deepest champions are the
hardest fights in the game — harder than anything under floor ten. Fight #50
is the Founder's Bout: Ondo Marr, the pit master, steps into their own ring
one time. Past the listed titles, every 10th win is an Apex rematch (cred and
purse only).

Regular bouts pay no XP, no credits, no drops (combat's arena flag handles
that) — one point of cred per win. The Pit pays in reputation, and keeps the
book: a leaderboard of named fighters the player's record is spliced into.
"""

import random as _random

from game import combat, data, inventory, places
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
    """Step into the ring: full HP, no companion (no seconds), arena rules."""
    cfg = _config()
    if player.location != cfg["venue"]:
        raise GameError("Fights start in the tank — step down into the Pit first.")
    if not places.is_open(cfg["venue"], clock):
        raise GameError(data.load("venues")[cfg["venue"]]["closed_line"])
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
        # The pit master announces title bouts personally — except their own.
        if bout["enemy"]["id"] == "ondo_the_bell":
            line = (
                "Ondo hands the bell rope to a stranger and steps into their own "
                "ring. The Pit makes a sound you will never hear again."
            )
        else:
            line = (
                f"Ondo rings the bell themself. “{bout['title']},” they call, and the Pit answers."
            )
        player.combat["log"].insert(0, f"CHAMPIONSHIP — {line}")
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
        # Beating a named champion is a fact the city remembers — the same
        # marker dungeon boss victories leave (dialogue and companions key on it).
        marker = f"defeated:{champ['enemy']}"
        if marker not in player.fired_events:
            player.fired_events.append(marker)
    player.street_cred += cred
    outcome["cred_gained"] = cred
    outcome["street_cred"] = player.street_cred
    outcome["crowd"] = cfg["crowd_lines"].get(cred_stage(player.street_cred))
    return outcome


def leaderboard(player):
    """The book: named fighters ranked by wins, the player spliced in. On a
    tie the named fighter ranks first — they got there before you."""
    rows = [dict(row) for row in _config()["leaderboard"]]
    rows.append(
        {
            "name": player.current_identity.get("name", "You"),
            "wins": player.arena_wins,
            "note": cred_stage(player.street_cred),
            "you": True,
        }
    )
    rows.sort(key=lambda row: (-row["wins"], row.get("you", False)))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows


def belts(player):
    """The belt rack: each title, who holds it, and whether you've taken it."""
    rack = []
    for number, spec in sorted(_config()["championships"].items(), key=lambda kv: int(kv[0])):
        claimed = player.arena_wins >= int(number)
        enemy = data.load("enemies")[spec["enemy"]]
        rack.append(
            {
                "number": int(number),
                "title": spec["title"],
                "holder": enemy["name"],
                "claimed": claimed,
            }
        )
    return rack


def _bell_line(player):
    """Ondo's ringside greeting — the pit master tracks your record closer
    than you do."""
    wins = player.arena_wins
    if "defeated:ondo_the_bell" in player.fired_events:
        return (
            "Ondo catches your eye from the bell rope and — for you, only for "
            "you — inclines their head."
        )
    if wins == 0:
        return "Ondo studies you from the bell rope. “New name. Say it like you plan to keep it.”"
    if wins < 10:
        return (
            f"“{wins} on the book,” Ondo says without checking it. “The Gatekeeper waits at ten.”"
        )
    if wins < 40:
        return "Ondo marks your walk-in with a slow nod. Your page in the book has history now."
    if wins < 50:
        return "“The card runs out at the top, little bell,” Ondo says, and doesn't look away."
    return "Ondo watches you the way the crowd watches Ondo."


def view(player, clock=None):
    """The Pit's card, record, book, and standing for the API."""
    cfg = _config()
    venue = data.load("venues").get(cfg["venue"], {})
    return {
        "name": cfg["name"],
        "venue": cfg["venue"],
        "district": cfg["district"],
        "blurb": cfg["blurb"],
        "energy": cfg["energy"],
        "minutes": cfg["minutes"],
        "hours": venue.get("hours"),
        "open": places.is_open(cfg["venue"], clock) if clock else True,
        "closed_line": venue.get("closed_line"),
        "wins": player.arena_wins,
        "titles": min(player.arena_wins // 10, len(cfg["championships"])),
        "street_cred": player.street_cred,
        "cred_stage": cred_stage(player.street_cred),
        "next": next_bout(player),
        "founder": cfg["founder"],
        "bell_line": _bell_line(player),
        "leaderboard": leaderboard(player),
        "belts": belts(player),
    }
