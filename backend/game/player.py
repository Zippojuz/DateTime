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

from game.character import Character
from game.errors import GameError

# Identity fields captured at creation.
IDENTITY_FIELDS = ("name", "pronouns", "appearance", "body")

# Aspects that can EVER change post-creation (name/species cannot). Whether one
# can change *right now* also requires it to be in ``unlocked_transformations``.
MUTABLE_IDENTITY_ASPECTS = ("appearance", "pronouns", "body")

DEFAULT_SPECIES = "human"
MAX_ENERGY = 100
STARTING_LOCATION = "docking_quarter"  # your ship docks here
STARTING_CREDITS = 50
STARTING_DEBT = 500  # the debt that brought you here
DEBT_DUE_WEEK = 52  # due by the end of the in-game year

# A couple of ship rations to start with.
DEFAULT_INVENTORY = {"protein_cube": 2}

# A small starting opinion set (expandable). Changeable later via the (future)
# difficult preference-change mechanic.
DEFAULT_PREFERENCES = {
    "books": {"sentiment": "love"},
    "nightlife": {"sentiment": "dislike"},
}


class Player(Character):
    def __init__(
        self,
        identity,
        species=DEFAULT_SPECIES,
        trait="",
        attributes=None,
        energy=MAX_ENERGY,
        created_identity=None,
        unlocked_transformations=None,
        preferences=None,
        location=STARTING_LOCATION,
        credits=STARTING_CREDITS,
        debt=STARTING_DEBT,
        debt_due_week=DEBT_DUE_WEEK,
        fired_events=None,
        inventory=None,
        combat_level=1,
        combat_xp=0,
        difficulty="normal",
        max_floor=0,
        dungeon=None,
        combat=None,
        equipment=None,
        companion="",
        protocols=None,
        last_gig_day=0,
        street_cred=0,
        arena_wins=0,
        gossip_day=0,
        tea_day=0,
        tea_id="",
        research_day=0,
        date=None,
        pawned=None,
        transcript=None,
        enrollment=None,
        class_day=0,
    ):
        # Character base handles name + registry attributes + preferences. The
        # player's name is their identity name (never changeable via transform).
        super().__init__(identity.get("name", ""), attributes, preferences)
        self.species = species
        # Species trait id (data/species.json key; "" = none). Chosen at
        # creation and locked, like the rest of the created identity.
        self.trait = trait
        self.energy = energy
        self.location = location
        self.credits = credits
        self.debt = debt
        self.debt_due_week = debt_due_week
        self.fired_events = list(fired_events or [])
        self.inventory = dict(inventory) if inventory is not None else {}
        # Combat progression persists across dungeon runs ("remember your level").
        self.combat_level = combat_level
        self.combat_xp = combat_xp
        self.difficulty = difficulty
        self.max_floor = max_floor
        self.dungeon = dict(dungeon) if dungeon else {}
        self.combat = dict(combat) if combat else {}
        # {slot: {"item": item_id, "gems": [gem_id | None, ...]}}. Gems live on
        # the equipped slot (inventory is quantity-based, not per-instance).
        self.equipment = dict(equipment) if equipment else {}
        # Recruited dungeon companion (npc id, "" = delving solo).
        self.companion = companion
        # Wetware protocols learned from data-shards (list of protocol ids).
        self.protocols = list(protocols or [])
        # Last absolute day a fixer gig was worked (0 = never; one gig per day).
        self.last_gig_day = last_gig_day
        # Reputation: championships and depth records make you a name.
        self.street_cred = street_cred
        # Arena win ladder (losses don't advance it; every 10th win is a title).
        self.arena_wins = arena_wins
        # Last absolute day Night Market gossip was picked up (one per night).
        self.gossip_day = gossip_day
        # Gantry 9 tea service: what's steeping (menu id) and the day it was
        # poured — the effect expires at midnight (see game/teahouse.py).
        self.tea_day = tea_day
        self.tea_id = tea_id
        # Last absolute day the Stacks' research desk was worked (one pull/day).
        self.research_day = research_day
        # Mid-outing state ({} = not on a date): {npc, venue, beat, gained}.
        # See game/dating.py — the scene spans several requests.
        self.date = dict(date) if date else {}
        # Forget-Me-Not's shelf: pawned items awaiting buyback, oldest first.
        # Each: {item, paid, buyback, day}. See game/pawnshop.py.
        self.pawned = list(pawned or [])
        # The Lyceum & library reading rooms (see game/university.py):
        #   transcript — completed course ids; capstone perks resolve from it.
        #   enrollment — the active 300/400 term: {course, sessions_done} ({} = none).
        #   class_day  — last absolute day a class was attended (one/day).
        self.transcript = list(transcript or [])
        self.enrollment = dict(enrollment) if enrollment else {}
        self.class_day = class_day
        self.current_identity = dict(identity)
        # Locked snapshot — never mutated after creation.
        self.created_identity = dict(created_identity or identity)
        self.unlocked_transformations = list(unlocked_transformations or [])

    @classmethod
    def create(cls, identity, species=DEFAULT_SPECIES, trait=""):
        """Fresh player. Identity is locked: current == created. Species is
        free text — data/species.json only offers suggestions — and carries a
        trait (see game/traits.py): registry species bring their own; custom
        species may pick any, or none."""
        clean = {field: identity.get(field, "") for field in IDENTITY_FIELDS}
        return cls(
            identity=clean,
            created_identity=clean,
            species=species,
            trait=trait,
            preferences=DEFAULT_PREFERENCES,
            inventory=dict(DEFAULT_INVENTORY),
        )

    def transform(self, changes):
        """Apply identity changes. Rejects immutable or still-locked aspects."""
        for aspect, value in changes.items():
            if aspect not in MUTABLE_IDENTITY_ASPECTS:
                raise GameError(f"'{aspect}' can't be changed through transformation.")
            if aspect not in self.unlocked_transformations:
                raise GameError(f"Transformation of {aspect} isn't unlocked yet.")
            self.current_identity[aspect] = str(value)

    def to_dict(self):
        base = super().to_dict()  # {name, attributes}
        base.update(
            {
                "species": self.species,
                "trait": self.trait,
                "energy": self.energy,
                "location": self.location,
                "credits": self.credits,
                "debt": self.debt,
                "debt_due_week": self.debt_due_week,
                "inventory": dict(self.inventory),
                "combat_level": self.combat_level,
                "combat_xp": self.combat_xp,
                "difficulty": self.difficulty,
                "max_floor": self.max_floor,
                "equipment": {k: dict(v) for k, v in self.equipment.items()},
                "companion": self.companion,
                "protocols": list(self.protocols),
                "last_gig_day": self.last_gig_day,
                "street_cred": self.street_cred,
                "arena_wins": self.arena_wins,
                "transcript": list(self.transcript),
                "enrollment": dict(self.enrollment),
                "identity": dict(self.current_identity),
                "created_identity": dict(self.created_identity),
                "unlocked_transformations": list(self.unlocked_transformations),
            }
        )
        return base
