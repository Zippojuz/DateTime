"""Preferences & opinions: likes/loves/dislikes/hates over topics.

Topics live in data/topics.json (a small, expandable registry). A character's
preferences are a map topic_id -> {sentiment, changeable}; only non-neutral
opinions are stored (absent = neutral). Both the player and NPCs have them (the
`Character` base holds them).

Compatibility is deliberately asymmetric (design intent): a character doesn't
much care whether a partner *shares* their likes, but strongly dislikes a
partner who is *opposed* to something they feel strongly about. Alignment on a
strong feeling gives only a small bond.
"""

from game import data

SENTIMENTS = ("love", "like", "neutral", "dislike", "hate")

# Numeric intensity, signed by valence.
SENTIMENT_VALUE = {"love": 2, "like": 1, "neutral": 0, "dislike": -1, "hate": -2}


def build_preferences(overrides=None):
    """Validate overrides against the topic registry. Stores only non-neutral
    opinions; unknown topics / invalid sentiments are dropped."""
    overrides = overrides or {}
    topics = data.load("topics")
    result = {}
    for topic_id, spec in overrides.items():
        if topic_id not in topics:
            continue
        sentiment = spec.get("sentiment", "neutral")
        if sentiment not in SENTIMENT_VALUE or sentiment == "neutral":
            continue
        changeable = spec.get("changeable", topics[topic_id].get("changeable", True))
        result[topic_id] = {"sentiment": sentiment, "changeable": bool(changeable)}
    return result


def sentiment_of(preferences, topic_id):
    entry = preferences.get(topic_id)
    return entry["sentiment"] if entry else "neutral"


def compatibility_delta(npc_sentiment, player_sentiment):
    """Affection change from the NPC learning the player's stance on a topic.

    Opposed feelings hurt (scaled by both intensities); a shared *strong* feeling
    gives a small +1; everything else is neutral. Alignment is never required.
    """
    a = SENTIMENT_VALUE.get(npc_sentiment, 0)
    b = SENTIMENT_VALUE.get(player_sentiment, 0)
    product = a * b
    if product < 0:
        return product  # -1 .. -4, opposition penalty
    if product >= 4:
        return 1  # both love (or both hate) — a small bond
    return 0


def activity_delta(npc_sentiment):
    """Reaction to a topic-themed activity (used once activities exist). A
    character favors their loves/likes and resents their dislikes/hates."""
    return SENTIMENT_VALUE.get(npc_sentiment, 0)
