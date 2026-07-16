"""Milestone 6: inventory, shop, rarity, gifting, and threshold dialogue."""

import pytest
from app import create_app
from game import dialogue, gifts, shop
from game.npc import NPC


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    return c


def _character(client, npc_id):
    return next(c for c in client.get("/api/characters").get_json() if c["id"] == npc_id)


# --- Inventory --------------------------------------------------------------


def test_starts_with_ship_rations(client):
    player = client.get("/api/game/state").get_json()["player"]
    assert player["inventory"] == {"protein_cube": 2}


def test_use_food_restores_energy_and_consumes(client):
    client.post("/api/action", json={"action": "explore"})  # energy 100 -> 90
    res = client.post("/api/item/use", json={"item_id": "protein_cube"}).get_json()
    assert res["used"]["energy"] == 15
    player = res["state"]["player"]
    assert player["energy"] == 100  # 90 + 15, capped
    assert player["inventory"]["protein_cube"] == 1


def test_cannot_use_a_gift_item(client):
    # Buy a gift, then try to "use" it.
    _buy(client, "club_pass")
    resp = client.post("/api/item/use", json={"item_id": "club_pass"})
    assert resp.status_code == 400


def test_cannot_use_what_you_dont_have(client):
    assert client.post("/api/item/use", json={"item_id": "stim_tea"}).status_code == 400


# --- Shop & rarity pricing --------------------------------------------------


def test_rarity_scales_price():
    items = shop.inventory.items()
    # Same base value (6); rarity multiplies: rare x8, legendary x20.
    assert shop.price(items["first_edition"]) == 48  # 6 * 8
    assert shop.price(items["aurora_pendant"]) == 120  # 6 * 20
    # District modifier applies on top.
    assert shop.price(items["first_edition"], 1.1) == 53  # round(48 * 1.1)


def test_shop_stock_is_district_specific(client):
    # Step into the Docking Quarter's stalls — theirs, not the Bloom Bazaar's.
    client.post("/api/travel", json={"to": "dockside_stalls", "mode": "walk"})
    shop_here = client.get("/api/shop").get_json()
    ids = [i["id"] for i in shop_here["stock"]]
    assert "star_ration" in ids
    assert "aurora_pendant" not in ids  # legendary, Bloom District only


def test_buy_spends_credits_and_adds_item(client):
    res = _buy(client, "club_pass").get_json()
    # club_pass: value 3, common x1, docking mod 0.8 -> round(2.4) = 2
    assert res["bought"]["cost"] == 2
    player = res["state"]["player"]
    assert player["credits"] == 48
    assert player["inventory"]["club_pass"] == 1


def test_cannot_buy_what_isnt_stocked_here(client):
    client.post("/api/travel", json={"to": "dockside_stalls", "mode": "walk"})
    resp = client.post("/api/shop/buy", json={"item_id": "aurora_pendant"})
    assert resp.status_code == 400


# --- Gifting ----------------------------------------------------------------


def _buy(client, item_id):
    """Stores are places now: duck into the Dockside Stalls (free, instant),
    buy, and step back onto the street."""
    client.post("/api/travel", json={"to": "dockside_stalls", "mode": "walk"})
    res = client.post("/api/shop/buy", json={"item_id": item_id})
    client.post("/api/travel", json={"to": "docking_quarter", "mode": "walk"})
    return res


def _reach_carro(client):
    # Carro is in the Docking Quarter (start). Advance to 10:00 (his stall).
    for _ in range(2):
        client.post("/api/action", json={"action": "wait"})


def test_gift_reaction_uses_preferences():
    vael = NPC.load("vael")  # loves books, hates nightlife
    book = shop.inventory.items()["paper_book"]  # uncommon books gift
    club = shop.inventory.items()["club_pass"]  # common nightlife gift
    loved = gifts.reaction(book, vael)
    hated = gifts.reaction(club, vael)
    assert loved["delta"] == 7  # love(6) + uncommon(1)
    assert loved["sentiment"] == "love"
    assert hated["delta"] == -4  # hate(-4), common bonus 0
    assert hated["sentiment"] == "hate"


def test_rarity_softens_but_never_flips_a_bad_gift():
    vael = NPC.load("vael")  # hates nightlife
    # A hypothetical legendary nightlife gift: hate(-4) + legendary(4)//2 = -2.
    fake = {"topic": "nightlife", "rarity": "legendary", "value": 1}
    react = gifts.reaction(fake, vael)
    assert react["delta"] == -2  # softened, still negative


def test_giving_a_gift_raises_affection_and_reveals_topic(client):
    _reach_carro(client)  # Carro loves nightlife
    _buy(client, "club_pass")  # a nightlife gift
    res = client.post("/api/gift", json={"npc_id": "carro", "item_id": "club_pass"}).get_json()
    assert res["reaction"]["sentiment"] == "love"
    assert res["reaction"]["delta"] == 6  # love(6) + common(0)
    # Carro starts at -5 disposition; +6 -> 1.
    assert res["affection"] == 1
    # The gift consumed the item and revealed his stance on nightlife.
    assert "club_pass" not in res["state"]["player"]["inventory"]
    carro = _character(client, "carro")
    assert carro["preferences"]["nightlife"]["sentiment"] == "love"


def test_one_gift_per_day(client):
    _reach_carro(client)
    _buy(client, "club_pass")
    _buy(client, "match_ticket")
    first = client.post("/api/gift", json={"npc_id": "carro", "item_id": "club_pass"})
    assert first.status_code == 200
    second = client.post("/api/gift", json={"npc_id": "carro", "item_id": "match_ticket"})
    assert second.status_code == 400
    assert "today" in second.get_json()["error"].lower()


def test_cannot_gift_across_districts(client):
    _reach_carro(client)
    _buy(client, "paper_book")  # not stocked here; the 400 is fine, we just need distance
    # Vael is in the Citadel Ring; gifting her from the docks is blocked.
    resp = client.post("/api/gift", json={"npc_id": "vael", "item_id": "protein_cube"})
    assert resp.status_code == 400


# --- Threshold dialogue (relationship arcs) ---------------------------------


def test_threshold_dialogue_selection():
    # Below the threshold -> intro; at/above -> the deeper scene.
    assert dialogue.tree_for_npc("vael", affection=0)["id"] == "vael_intro"
    assert dialogue.tree_for_npc("vael", affection=14)["id"] == "vael_intro"
    assert dialogue.tree_for_npc("vael", affection=15)["id"] == "vael_close"


def test_stage_labels():
    from game import social

    assert social.stage(0) == "stranger"
    assert social.stage(12) == "acquaintance"
    assert social.stage(30) == "friend"
    assert social.stage(60) == "close"
    assert social.stage(-30) == "hostile"
