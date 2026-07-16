"""Species traits: one shared knack per registry species (game/traits.py),
plus the amended Identity Philosophy rule — species may flavor dialogue and
gate minor content, but the main romance pathway stays open to everyone."""

import pytest
from app import create_app
from game import combat, data, dialogue, dungeon, shop, traits, world
from game.actions import apply_action
from game.calendar import GameClock
from game.errors import GameError
from game.player import Player


class QuietRng:
    def uniform(self, a, b):
        return 1.0

    def random(self):
        return 0.99  # never dodge, never crit, never flee by luck

    def choice(self, seq):
        return seq[0]

    def randint(self, a, b):
        return b


def _traited(trait, location="docking_quarter"):
    p = Player.create({"name": "Kai", "pronouns": "she/her"}, trait=trait)
    p.location = location
    return p


def test_every_registry_species_carries_a_trait():
    registry = data.load("species")
    for sid, entry in registry.items():
        trait = entry.get("trait")
        assert trait and trait["name"] and trait["blurb"] and trait["effects"], sid


def test_trait_effect_resolution():
    assert traits.effect(_traited("hivemind"), "action_energy_mult") == 0.75
    assert traits.effect(_traited(""), "action_energy_mult", 1.0) == 1.0
    assert traits.default_for_species("Self-Owned Chassis") == "chassis"
    assert traits.default_for_species("Sentient fog (rude)") == ""


# --- The daily loop -----------------------------------------------------------------


def test_maintenance_cycle_rests_in_four_hours():
    chassis, meat = _traited("chassis"), _traited("")
    c1, c2 = GameClock(), GameClock()
    apply_action(chassis, c1, "rest")
    apply_action(meat, c2, "rest")
    assert c1.minute_of_day == 8 * 60 + 240
    assert c2.minute_of_day == 8 * 60 + 480
    assert chassis.energy == meat.energy == 100


def test_shift_change_discounts_action_energy():
    hive = _traited("hivemind")
    apply_action(hive, GameClock(), "explore")  # -10 -> -8 (round(-7.5))
    assert hive.energy == 100 - 8
    hive.energy = 100
    apply_action(hive, GameClock(), "train", "charm")  # -15 -> -11
    assert hive.energy == 100 - 11


def test_photosynthesis_feeds_on_daylight():
    moss = _traited("mycoid")
    moss.energy = 50
    clock = GameClock()  # 08:00 — daylight
    apply_action(moss, clock, "wait")
    assert moss.energy == 55
    apply_action(moss, clock, "explore")
    assert moss.energy == 60
    clock.advance(10 * 60)  # past 18:00 — night rules
    apply_action(moss, clock, "explore")
    assert moss.energy == 50  # -10, no sun to sip


def test_rooftop_lines_halve_walks_and_priced_in_rides_free():
    bird = _traited("avian")
    cost = world.travel(bird, GameClock(), "the_grid", "walk")
    assert cost["minutes"] == 10  # adjacent walk: 20 -> 10

    suit = _traited("human")
    suit.credits = 0  # broke, but the reader knows their face
    cost = world.travel(suit, GameClock(), "the_grid", "transit")
    assert cost["credits"] == 0
    assert suit.credits == 0


def test_priced_in_discounts_the_sticker():
    suit, nobody = _traited("human", "static_bazaar"), _traited("", "static_bazaar")
    suit.credits = nobody.credits = 5000
    item = data.load("items")["reflex_splice"]
    base_mod = data.load("shops")["static_bazaar"]["price_mod"]
    full = shop.price(item, base_mod)
    listed = {i["id"]: i["price"] for i in shop.stock("static_bazaar", discount=0.1)}
    assert listed["reflex_splice"] == round(full * 0.9) or listed["reflex_splice"] < full
    paid = shop.buy(suit, GameClock(), "reflex_splice")["cost"]
    sticker = shop.buy(nobody, GameClock(), "reflex_splice")["cost"]
    assert paid < sticker


# --- Combat -------------------------------------------------------------------------


def test_built_for_it_adds_hp_and_braces_harder():
    tank, meat = _traited("warform"), _traited("")
    assert combat.player_stats(tank)["max_hp"] == round(combat.player_stats(meat)["max_hp"] * 1.1)


def test_escape_artist_always_finds_the_seam():
    fox = _traited("uplift")
    state = combat.start(fox, "holo_siren", 1, 100)
    combat.act(fox, state, "flee", rng=QuietRng())  # QuietRng would never flee by luck
    assert state["fled"] is True
    # Bosses still corner you — the trait doesn't override the boss rule.
    fox.combat = {}
    state = combat.start(fox, "nyx_deep_signal", 10, 100)
    with pytest.raises(GameError, match="won't let you leave"):
        combat.act(fox, state, "flee", rng=QuietRng())
    assert combat.player_stats(fox)["dodge"] > combat.player_stats(_traited(""))["dodge"]


def test_patient_metabolism_shortens_statuses():
    assert combat._resisted_turns(_traited("reptilian"), 3) == 2
    assert combat._resisted_turns(_traited("reptilian"), 1) == 1  # never below one
    assert combat._resisted_turns(_traited(""), 3) == 3


def test_native_signal_runs_hotter_and_enters_cheap():
    born, meat = _traited("substrate_born"), _traited("")
    assert combat.player_stats(born)["heat_cap"] == combat.player_stats(meat)["heat_cap"] + 15
    born.location = meat.location = dungeon.ENTRANCE_DISTRICT
    dungeon.enter(born, GameClock(), seed=3)
    dungeon.enter(meat, GameClock(), seed=3)
    assert born.energy - meat.energy == 5  # half the 10-energy toll


# --- Dialogue: species color, never a closed road -----------------------------------


def test_species_choices_hide_from_other_species():
    tree = dialogue.tree_by_id("oona_intro")
    fox, meat = _traited("uplift"), _traited("")
    fox_texts = [c["text"] for c in dialogue.node_view(tree, "n4", fox)["choices"]]
    assert any("I know that paperwork" in t for t in fox_texts)
    meat_texts = [c["text"] for c in dialogue.node_view(tree, "n4", meat)["choices"]]
    assert not any("I know that paperwork" in t for t in meat_texts)
    # Choosing it blind is refused, not just hidden.
    gated_index = next(
        i for i, c in enumerate(tree["nodes"]["n4"]["choices"]) if c.get("requires_trait")
    )
    with pytest.raises(GameError, match="requirement"):
        dialogue.resolve_choice(tree, "n4", gated_index, meat)
    next_id, choice = dialogue.resolve_choice(tree, "n4", gated_index, fox)
    assert next_id == "n5" and choice["affection"] == 5


def test_the_main_pathway_is_never_species_gated():
    """The amended Identity Philosophy's hard rule, enforced: every dialogue
    node keeps at least one choice free of species/event gates."""
    for tree in data.load("dialogues").values():
        for node_id, node in tree["nodes"].items():
            if not node["choices"]:
                continue  # terminal beat — nothing to gate
            open_roads = [
                c
                for c in node["choices"]
                if not c.get("requires_trait") and not c.get("requires_event")
            ]
            assert open_roads, f"{tree['id']}:{node_id} has no species-agnostic path"


# --- Creation flow -------------------------------------------------------------------


@pytest.fixture
def client():
    return create_app().test_client()


def test_registry_species_bring_their_trait(client):
    res = client.post(
        "/api/game/new", json={"name": "Kai", "pronouns": "she/her", "species": "Warform"}
    )
    assert res.get_json()["player"]["trait"] == "warform"


def test_custom_species_may_pick_any_trait_or_none(client):
    res = client.post(
        "/api/game/new",
        json={
            "name": "Kai",
            "pronouns": "she/her",
            "species": "Sentient fog (rude)",
            "trait": "hivemind",
        },
    )
    assert res.get_json()["player"]["trait"] == "hivemind"
    res = client.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Sentient fog (rude)", "trait": ""},
    )
    assert res.get_json()["player"]["trait"] == ""
    res = client.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "trait": "not_a_trait"},
    )
    assert res.status_code == 400


def test_the_tell_glows_through_the_dialogue_api(client):
    client.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Bioluminescent"},
    )
    for _ in range(2):  # Vex holds court from noon; game starts 08:00
        client.post("/api/action", json={"action": "wait"})
    client.post("/api/action", json={"action": "wait"})
    client.post("/api/action", json={"action": "wait"})
    client.post("/api/action", json={"action": "wait"})
    start = client.post("/api/dialogue/start", json={"npc_id": "vex"}).get_json()
    res = client.post(
        "/api/dialogue/choose",
        json={
            "npc_id": "vex",
            "dialogue_id": start["dialogue_id"],
            "node_id": start["node"]["node_id"],
            "choice_index": 0,  # affection 2 -> The Tell makes it 3
        },
    ).get_json()
    assert res["gained"] == 3
