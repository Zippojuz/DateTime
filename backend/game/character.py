"""Shared Character model backing BOTH the player and NPCs.

Attributes are defined once in data/attributes.json (the registry) and stored as
a keyed map. NPCs mirror the player's attribute set; per-character overrides in
characters.json merge over the registry defaults. Adding a new attribute is a
one-line registry entry — no code or schema change.
"""

from game import data


def _clamp(value, low, high):
    return max(low, min(high, value))


def build_attributes(overrides=None):
    """Return a full attribute map: registry defaults with overrides applied,
    each clamped to its registry min/max.

    Unknown override keys are ignored, so stale or hand-edited data can't inject
    phantom attributes.
    """
    overrides = overrides or {}
    registry = data.attributes()
    result = {}
    for attr_id, spec in registry.items():
        value = overrides.get(attr_id, spec["default"])
        result[attr_id] = _clamp(int(value), spec["min"], spec["max"])
    return result


class Character:
    """A named entity with attributes drawn from the shared registry.

    Base class for both the player and NPCs, so they share one attribute model.
    """

    def __init__(self, name, attributes=None):
        self.name = name
        self.attributes = build_attributes(attributes)

    def to_dict(self):
        return {"name": self.name, "attributes": dict(self.attributes)}
