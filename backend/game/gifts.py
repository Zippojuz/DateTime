"""Gifting: give an item to an NPC and let their preferences decide. (Milestone 6)

The reaction is driven by how the NPC feels about the gift's topic — loved
topics land big, hated ones backfire. Rarity adds an effort bonus on top, but a
gift they hate still stings (rarity only softens it, never flips it positive).
Giving a gift also reveals the NPC's stance on that topic (discovery by action).
"""

from game import preferences

# Base affection change from the NPC's sentiment toward the gift's topic.
SENTIMENT_GIFT = {"love": 6, "like": 3, "neutral": 1, "dislike": -2, "hate": -4}

# Effort bonus from rarity (full on positive reactions, halved on negative ones).
RARITY_GIFT_BONUS = {"common": 0, "uncommon": 1, "rare": 2, "legendary": 4}


def reaction(item, npc):
    """Compute a gift reaction: {delta, sentiment, topic}.

    Positive/neutral reactions get the full rarity bonus. Negative reactions get
    only half the bonus and stay negative — a fancy thing they hate is still a
    thing they hate.
    """
    topic = item.get("topic")
    sentiment = preferences.sentiment_of(npc.preferences, topic) if topic else "neutral"
    base = SENTIMENT_GIFT[sentiment]
    bonus = RARITY_GIFT_BONUS.get(item.get("rarity", "common"), 0)

    if base >= 0:
        delta = base + bonus
    else:
        delta = min(-1, base + bonus // 2)

    return {"delta": delta, "sentiment": sentiment, "topic": topic}
