"""Player model: stats, energy, and identity. (Milestone 1)

IMPORTANT — Identity policy (see dtDesignDoc.md -> Identity Philosophy):
Identity fields (pronouns, gender, orientation, appearance, body) are free-form
data. They are NEVER used to gate content — no code path may branch on them to
restrict a route, scene, or dialogue option. Every character is always
romanceable.

Player identity is locked at creation into an immutable ``created_identity``
snapshot; a mutable ``current_identity`` starts equal to it and only changes via
the story-gated transformation system (see PLAN.md -> Milestone 1).
"""

# Core stats from the design doc.
STATS = ("charm", "wit", "courage", "empathy")

# Aspects of identity that can be changed later — but only once the matching
# transformation capability has been unlocked through the story.
MUTABLE_IDENTITY_ASPECTS = ("appearance", "pronouns", "body")


class Player:
    """Stub. Full implementation (creation, energy, transform) lands in M1."""

    pass
