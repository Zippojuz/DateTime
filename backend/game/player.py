"""Player model: attributes, energy, and identity. (Milestone 1)

IMPORTANT — Identity policy (see dtDesignDoc.md -> Identity Philosophy):
Identity fields (pronouns, gender, orientation, appearance, body) are free-form
data. They are NEVER used to gate content — no code path may branch on them to
restrict a route, scene, or dialogue option. Every character is always
romanceable.

Player identity is locked at creation into an immutable ``created_identity``
snapshot; a mutable ``current_identity`` starts equal to it and only changes via
the story-gated transformation system (``transform``), which requires the
matching aspect to have been unlocked.
"""

from game.character import build_attributes
from game.errors import GameError

# Identity fields captured at creation.
IDENTITY_FIELDS = ("name", "pronouns", "appearance", "body")

# Aspects that can EVER change post-creation (name/species cannot). Whether one
# can change *right now* also requires it to be in ``unlocked_transformations``.
MUTABLE_IDENTITY_ASPECTS = ("appearance", "pronouns", "body")

DEFAULT_SPECIES = "human"
MAX_ENERGY = 100


class Player:
    def __init__(
        self,
        identity,
        species=DEFAULT_SPECIES,
        attributes=None,
        energy=MAX_ENERGY,
        created_identity=None,
        unlocked_transformations=None,
    ):
        self.species = species
        self.attributes = build_attributes(attributes)
        self.energy = energy
        self.current_identity = dict(identity)
        # Locked snapshot — never mutated after creation.
        self.created_identity = dict(created_identity or identity)
        self.unlocked_transformations = list(unlocked_transformations or [])

    @classmethod
    def create(cls, identity):
        """Fresh player. Identity is locked: current == created."""
        clean = {field: identity.get(field, "") for field in IDENTITY_FIELDS}
        return cls(identity=clean, created_identity=clean)

    def transform(self, changes):
        """Apply identity changes. Rejects immutable or still-locked aspects."""
        for aspect, value in changes.items():
            if aspect not in MUTABLE_IDENTITY_ASPECTS:
                raise GameError(f"'{aspect}' can't be changed through transformation.")
            if aspect not in self.unlocked_transformations:
                raise GameError(f"Transformation of {aspect} isn't unlocked yet.")
            self.current_identity[aspect] = str(value)

    def to_dict(self):
        return {
            "species": self.species,
            "attributes": dict(self.attributes),
            "energy": self.energy,
            "identity": dict(self.current_identity),
            "created_identity": dict(self.created_identity),
            "unlocked_transformations": list(self.unlocked_transformations),
        }
