"""Dialogue tree runner + pronoun helper. (Milestone 2)

Trees are authored in data/dialogues.json, keyed by dialogue id. A node has
`text` and `choices`; a choice has `text`, `next` (node id or null to end),
optional `affection`, optional `requires` (attribute thresholds — a light
stat gate, shown locked), optional `requires_event` (a fired-event marker
like "defeated:ondo_the_bell" — hidden entirely until it's true, so story
payoffs don't spoil themselves as grayed-out options), and optional
`requires_trait` (a species trait id — hidden the same way; per the amended
Identity Philosophy these are bonus color only, and an integrity test
guarantees every node keeps a trait-free path). Choice text is rendered
through the pronoun helper so player (and NPC) references resolve correctly,
respecting the player's *current* pronouns.
"""

from game import data
from game.errors import GameError

# Full grammatical forms for the presets; graceful fallback for custom sets.
PRONOUN_SETS = {
    "she/her": {
        "subj": "she",
        "obj": "her",
        "pos": "her",
        "pos_pron": "hers",
        "reflex": "herself",
    },
    "he/him": {
        "subj": "he",
        "obj": "him",
        "pos": "his",
        "pos_pron": "his",
        "reflex": "himself",
    },
    "they/them": {
        "subj": "they",
        "obj": "them",
        "pos": "their",
        "pos_pron": "theirs",
        "reflex": "themself",
    },
}


def pronouns_for(pronoun_str):
    if pronoun_str in PRONOUN_SETS:
        return PRONOUN_SETS[pronoun_str]
    parts = [p.strip() for p in (pronoun_str or "").split("/")]
    subj = parts[0] if parts and parts[0] else "they"
    obj = parts[1] if len(parts) > 1 and parts[1] else subj
    return {"subj": subj, "obj": obj, "pos": obj, "pos_pron": obj, "reflex": f"{subj}self"}


def render_pronouns(text, name="", pronouns="they/them"):
    """Substitute {name} and pronoun tokens ({subj}/{obj}/{pos}/{pos_pron}/
    {reflex}, plus capitalized variants) into `text`."""
    p = pronouns_for(pronouns)
    mapping = {
        "{name}": name,
        "{subj}": p["subj"],
        "{obj}": p["obj"],
        "{pos}": p["pos"],
        "{pos_pron}": p["pos_pron"],
        "{reflex}": p["reflex"],
        "{Subj}": p["subj"].capitalize(),
        "{Obj}": p["obj"].capitalize(),
        "{Pos}": p["pos"].capitalize(),
    }
    for token, value in mapping.items():
        text = text.replace(token, value)
    return text


def tree_by_id(dialogue_id):
    """Return a dialogue tree by its id, or None."""
    return data.load("dialogues").get(dialogue_id)


def tree_for_npc(npc_id, affection=0):
    """Return the best dialogue tree for an NPC given the current affection.

    Among the NPC's trees, pick the highest `requires_affection` that the player
    qualifies for (default requirement 0). This is how relationship arcs unlock:
    a deeper scene supersedes the intro once you're close enough.
    """
    best = None
    for tree in data.load("dialogues").values():
        if tree.get("npc") != npc_id:
            continue
        needed = tree.get("requires_affection", 0)
        if affection >= needed and (best is None or needed > best.get("requires_affection", 0)):
            best = tree
    return best


def _meets(player, requires):
    return all(player.attributes.get(attr, 0) >= threshold for attr, threshold in requires.items())


def node_view(tree, node_id, player):
    """A render-ready node: resolved text + choices with lock state."""
    node = tree["nodes"][node_id]
    name = player.current_identity.get("name", "")
    pronouns = player.current_identity.get("pronouns", "they/them")
    choices = []
    for index, choice in enumerate(node["choices"]):
        event = choice.get("requires_event")
        if event and event not in player.fired_events:
            continue  # hidden, not locked — indices stay stable via `index`
        trait = choice.get("requires_trait")
        if trait and getattr(player, "trait", "") != trait:
            continue  # species color: hidden from everyone else
        requires = choice.get("requires")
        choices.append(
            {
                "index": index,
                "text": render_pronouns(choice["text"], name, pronouns),
                "locked": bool(requires) and not _meets(player, requires),
                "requires": requires,
            }
        )
    return {
        "node_id": node_id,
        "text": render_pronouns(node["text"], name, pronouns),
        "choices": choices,
    }


def resolve_choice(tree, node_id, choice_index, player):
    """Validate a chosen option. Returns (next_node_id_or_None, choice_dict).

    The caller reads the choice's `affection`, `express`, `reveal_npc`, and
    `offense` fields to apply effects.
    """
    node = tree["nodes"].get(node_id)
    if node is None:
        raise GameError("That conversation thread no longer exists.")
    if not isinstance(choice_index, int) or not (0 <= choice_index < len(node["choices"])):
        raise GameError("Invalid choice.")
    choice = node["choices"][choice_index]
    requires = choice.get("requires")
    if requires and not _meets(player, requires):
        raise GameError("You don't meet the requirement for that option.")
    event = choice.get("requires_event")
    if event and event not in player.fired_events:
        raise GameError("You don't meet the requirement for that option.")
    trait = choice.get("requires_trait")
    if trait and getattr(player, "trait", "") != trait:
        raise GameError("You don't meet the requirement for that option.")
    return choice.get("next"), choice
