"""The Stacks — the Citadel Ring's archive (data/stacks.json).

The research desk: one pull a day, ninety minutes of microfiche. A file on
someone you've met reveals one preference you haven't discovered — slower
than guessing with gifts, but the archive is never wrong (and unlike Night
Market gossip, a file is a *source*: the discovery is marked).

One file isn't about a person at all. The draft in row nine — forty years of
tickets closed 'no fault found' — teaches anyone who researches it how to
see the unseen (the Archivist's Lens), which is the findable path to
perceiving Index. Substrate-Born hear them natively: the species opens the
door early, never exclusively (dtDesignDoc.md -> Identity Philosophy).
"""

from game import data, inventory, preferences, social
from game.errors import GameError
from game.npc import NPC, perceives_unseen


def _config():
    return data.load("stacks")


def _spend(player, clock, day):
    cfg = _config()["research"]
    if player.energy + cfg["energy"] < 0:
        raise GameError("Too tired to read microfiche — rest first.")
    player.energy = max(0, player.energy + cfg["energy"])
    player.research_day = day
    clock.advance(cfg["minutes"])


def research(save_id, player, clock, subject, day):
    """Work the research desk. Returns a result dict; raises GameError on any
    rule the desk enforces, KeyError for a subject the archive can't find."""
    cfg = _config()
    if player.location != cfg["venue"]:
        raise GameError("The desk is in the Stacks — files don't check out.")
    if player.research_day == day:
        raise GameError("One pull a day. The desk clerk taps the sign. There is no desk clerk.")

    draft = cfg["draft"]
    if subject == draft["subject"]:
        if perceives_unseen(player):
            raise GameError("You already know what the draft is. They know you know.")
        _spend(player, clock, day)
        inventory.add_item(player, draft["item"], 1)
        player.fired_events.append(draft["event"])
        return {"subject": draft["subject"], "text": draft["text"], "unlocked": "index"}

    plant = cfg["plant_7"]
    if subject == plant["subject"]:
        if plant["event"] in player.fired_events:
            raise GameError(
                "The file is exactly as long as it was yesterday. "
                "Someone is maintaining it. You've read what survives."
            )
        _spend(player, clock, day)
        player.fired_events.append(plant["event"])
        return {"subject": plant["subject"], "text": plant["text"]}

    npc = NPC.load(subject)  # KeyError -> the route's 404
    if not npc.unlocked_for(player):
        raise KeyError(subject)  # don't leak the imperceivable
    rel = social.all_relationships(save_id, day).get(subject, {})
    if not rel.get("last_talked_day"):
        raise GameError(
            "The archive files people under who they are to you — meet them in person first."
        )
    known = set(rel.get("known_npc_topics", []))
    undiscovered = [t for t in sorted(npc.preferences) if t not in known]
    if not undiscovered:
        raise GameError(f"The file ends. You know everything the archive does about {npc.name}.")

    _spend(player, clock, day)
    topic = undiscovered[0]
    social.discover_npc_topic(save_id, subject, topic)
    sentiment = preferences.sentiment_of(npc.preferences, topic)
    topic_name = data.load("topics").get(topic, {}).get("name", topic)
    verdict = {
        "love": "the file practically sighs about it",
        "like": "annotated warmly, twice",
        "dislike": "a thin folder, closed hard",
        "hate": "the margin note is just an underline, three times",
    }.get(sentiment, "the record keeps its opinion to itself")
    return {
        "subject": subject,
        "npc": npc.name,
        "topic": topic,
        "sentiment": sentiment,
        "text": (
            f"A requisition slip, ninety minutes, and a folder that smells like dust: "
            f"{npc.name}, on the subject of {topic_name.lower()} — {verdict}."
        ),
    }
