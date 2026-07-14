"""NPC model — non-player characters (the romanceable cast and others).

NPCs subclass Character, so their attributes mirror the player's set from the
shared registry (with optional per-character overrides in characters.json). On
top of attributes, an NPC carries world-facing data loaded from that file:
pronouns, species, home district, personality, arc theme, and an availability
schedule.

Identity policy (see dtDesignDoc.md -> Identity Philosophy): an NPC's pronouns
and identity are data, never gates. Every NPC is romanceable by default.
"""

from game import data
from game.character import Character


class NPC(Character):
    def __init__(
        self,
        id,
        name,
        pronouns="they/them",
        species="",
        personality="",
        district=None,
        arc_theme="",
        romanceable=True,
        schedule=None,
        attributes=None,
        preferences=None,
        starting_disposition=0,
        companion=None,
    ):
        super().__init__(name, attributes, preferences)
        self.id = id
        self.pronouns = pronouns
        self.species = species
        self.personality = personality
        self.district = district
        self.arc_theme = arc_theme
        self.romanceable = romanceable
        # Combat spec if this NPC can be recruited to delve ({} = never delves).
        self.companion = dict(companion) if companion else {}
        # Where affection starts when the relationship is first seeded (0 =
        # neutral). Most NPCs start neutral; some may lean warm/cold.
        self.starting_disposition = starting_disposition
        # List of availability windows; each: {start, end, location, activity,
        # available}. Resolved against district hours in later milestones.
        self.schedule = schedule or []

    @classmethod
    def from_data(cls, entry):
        """Build an NPC from a characters.json entry. Attributes mirror the
        registry; the entry may override individual values via `attributes`."""
        return cls(
            id=entry["id"],
            name=entry["name"],
            pronouns=entry.get("pronouns", "they/them"),
            species=entry.get("species", ""),
            personality=entry.get("personality", ""),
            district=entry.get("district"),
            arc_theme=entry.get("arc_theme", ""),
            romanceable=entry.get("romanceable", True),
            schedule=entry.get("schedule", []),
            attributes=entry.get("attributes"),
            preferences=entry.get("preferences"),
            starting_disposition=entry.get("starting_disposition", 0),
            companion=entry.get("companion"),
        )

    @classmethod
    def load(cls, npc_id):
        """Load a single NPC from characters.json by id."""
        entry = data.characters().get(npc_id)
        if entry is None:
            raise KeyError(f"Unknown NPC: {npc_id!r}")
        return cls.from_data(entry)

    @classmethod
    def load_all(cls):
        """Load every NPC from characters.json, keyed by id."""
        return {cid: cls.from_data(entry) for cid, entry in data.characters().items()}

    def to_dict(self):
        base = super().to_dict()
        base.update(
            {
                "id": self.id,
                "pronouns": self.pronouns,
                "species": self.species,
                "personality": self.personality,
                "district": self.district,
                "arc_theme": self.arc_theme,
                "romanceable": self.romanceable,
                "schedule": self.schedule,
            }
        )
        return base
