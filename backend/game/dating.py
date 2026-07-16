"""THE DATING SYSTEM — outings (data/dates.json).

Ask a reachable someone out to a venue that hosts dates (the Steeps, the
Night Market, Gantry 9 — venue-keyed scenes, so new venues just add data).
A date is a small scene: an opening, a few choice beats, a closing — big
affection compared to the daily loop, once per NPC per week.

Scenes are NPC-agnostic but not NPC-flat: text renders through the pronoun
tokens, and a choice may carry a ``topic`` — the same date plays differently
opposite someone who loves nightlife than someone who hates it (their real
preferences modulate the affection, ±2). Never a reveal, just a read.

Rules the venue enforces: they must be reachable (you ask in person), warmer
than a stranger (acquaintance+), the venue must be open, and you cover both
— that's the custom. Mid-scene state rides on ``player.date``.
"""

from game import data, dialogue, places, preferences, social, world
from game.errors import GameError
from game.npc import NPC
from game.player import MAX_ENERGY

MIN_AFFECTION = 10  # acquaintance — you don't ask strangers to the baths
TOPIC_MODIFIER = {"love": 2, "like": 1, "dislike": -1, "hate": -2}


def scenes():
    return data.load("dates")


def _render(text, npc):
    return dialogue.render_pronouns(text, name=npc.name, pronouns=npc.pronouns)


def _beat_view(player, npc, scene, reply=None):
    """The current beat, rendered for the client."""
    beat_index = player.date["beat"]
    beat = scene["beats"][beat_index]
    view = {
        "npc": npc.id,
        "npc_name": npc.name,
        "venue": scene["venue"],
        "title": scene["title"],
        "beat": beat_index,
        "total_beats": len(scene["beats"]),
        "text": _render(beat["text"], npc),
        "choices": [{"index": i, "text": c["text"]} for i, c in enumerate(beat["choices"])],
        "gained": player.date["gained"],
        "done": False,
    }
    if beat_index == 0:
        view["opening"] = _render(scene["opening"], npc)
    if reply:
        view["reply"] = _render(reply, npc)
    return view


def start(save_id, player, clock, npc_id, venue, day, week):
    """Ask someone out and head to the venue together. Returns the first beat."""
    if player.date:
        raise GameError("You're already mid-outing — see it through.")
    scene = scenes().get(venue)
    if scene is None:
        raise GameError("Nobody dates there. Yet.")
    npc = NPC.load(npc_id)  # KeyError -> the route's 404
    if not npc.unlocked_for(player):
        raise KeyError(npc_id)

    av = world.availability(npc, clock)
    if not (av["available"] and av.get("district") == player.location):
        raise GameError(f"You ask someone out in person — find {npc.name} first.")
    affection = social.get_affection(save_id, npc_id, day)
    if affection < MIN_AFFECTION:
        raise GameError(
            _render(
                "{name} softens the refusal, but it is one: "
                "“We barely know each other. Ask me again when we do.”",
                npc,
            )
        )
    if social.has_dated_this_week(save_id, npc_id, week):
        raise GameError(_render("{name} touches your arm: “One outing a week. Keep me rare.”", npc))
    if not places.is_open(venue, clock):
        raise GameError(places.get(venue).get("closed_line", "It's closed right now."))
    if player.credits < scene["cost"]:
        raise GameError("You cover both — that's the custom. You can't tonight.")
    if scene["energy"] < 0 and player.energy + scene["energy"] < 0:
        raise GameError("Too tired for a good time — rest first.")

    player.credits -= scene["cost"]
    player.location = venue
    player.date = {"npc": npc_id, "venue": venue, "beat": 0, "gained": 0}
    return _beat_view(player, npc, scene)


def choose(save_id, player, clock, choice_index, day, week):
    """Play one beat of the active date. Returns the next beat, or the closing."""
    if not player.date:
        raise GameError("You're not on a date. (Bold, though.)")
    scene = scenes()[player.date["venue"]]
    npc = NPC.load(player.date["npc"])
    beat = scene["beats"][player.date["beat"]]
    if not isinstance(choice_index, int) or not (0 <= choice_index < len(beat["choices"])):
        raise GameError("That wasn't one of the options.")

    choice = beat["choices"][choice_index]
    gained = choice.get("affection", 0)
    # A topic-tagged move lands on who they actually are (±2, never a reveal).
    topic = choice.get("topic")
    if topic:
        gained += TOPIC_MODIFIER.get(preferences.sentiment_of(npc.preferences, topic), 0)
    if gained:
        social.add_opinion(save_id, npc.id, gained, day)
    player.date["gained"] += gained
    player.date["beat"] += 1

    if player.date["beat"] < len(scene["beats"]):
        return _beat_view(player, npc, scene, reply=choice.get("reply"))

    # The closing: completion bonus, the weekly mark, and the bill for time.
    total = player.date["gained"]
    social.add_opinion(save_id, npc.id, scene["bonus"], day)
    social.mark_dated(save_id, npc.id, week)
    player.date = {}
    player.energy = max(0, min(MAX_ENERGY, player.energy + scene["energy"]))
    clock.advance(scene["minutes"])
    good = total >= scene["good_threshold"]
    return {
        "npc": npc.id,
        "npc_name": npc.name,
        "venue": scene["venue"],
        "title": scene["title"],
        "done": True,
        "good": good,
        "reply": _render(choice.get("reply", ""), npc),
        "closing": _render(scene["closing_good" if good else "closing_flat"], npc),
        "gained": total + scene["bonus"],
        "affection": social.get_affection(save_id, npc.id, day),
    }


def leave(save_id, player, clock, week):
    """Walk out mid-date. Keeps what was gained, burns the week, half the time."""
    if not player.date:
        raise GameError("You're not on a date.")
    scene = scenes()[player.date["venue"]]
    npc = NPC.load(player.date["npc"])
    social.mark_dated(save_id, npc.id, week)
    player.date = {}
    clock.advance(scene["minutes"] // 2)
    return {
        "done": True,
        "left": True,
        "npc": npc.id,
        "npc_name": npc.name,
        "closing": _render(
            "{name} walks you to the door with the practiced grace of someone "
            "recataloguing an evening. “Another time, then.”",
            npc,
        ),
    }
