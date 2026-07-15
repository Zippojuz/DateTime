"""Species traits — one shared knack per registry species. (data/species.json)

A trait is the mechanical half of a species: like a D&D class, but reshaped
around what a body *is* rather than what it studied. Trait ids are species
ids; the trait a player carries is chosen at creation (a registry species
brings its own; a custom free-text species may pick any, or none) and is
locked with the rest of the created identity.

Per the amended Identity Philosophy (dtDesignDoc.md): traits and species may
flavor dialogue and gate minor content, but the main romance pathway is never
species-gated — every dialogue node keeps at least one trait-free path, which
data integrity tests enforce.

Effect keys and where they hook:
- transit_free, walk_minutes_mult ......... world.travel
- shop_discount ........................... shop pricing
- rest_minutes, action_energy_mult,
  photosynthesis .......................... actions.apply_action
- flee_always, dodge, max_hp_mult,
  telegraph_guard_divisor, heat_cap,
  status_turns_resist ..................... combat
- dungeon_enter_discount .................. dungeon.enter
- dialogue_affection_bonus, offense_extra . dialogue routes (The Tell)
"""

from game import data


def registry():
    """Every species' trait, keyed by species/trait id."""
    return {
        sid: {**entry["trait"], "id": sid}
        for sid, entry in data.load("species").items()
        if "trait" in entry
    }


def get(trait_id):
    """The trait spec for an id ('' or unknown -> None)."""
    entry = data.load("species").get(trait_id or "", {})
    return entry.get("trait")


def effect(player, key, default=None):
    """The player's value for one trait effect (default when untraited)."""
    trait = get(getattr(player, "trait", ""))
    if not trait:
        return default
    return trait.get("effects", {}).get(key, default)


def default_for_species(species_name):
    """The trait id a species name implies (registry names match case-
    insensitively; free-text species imply no trait)."""
    for sid, entry in data.load("species").items():
        if entry["name"].lower() == (species_name or "").lower() and "trait" in entry:
            return sid
    return ""
