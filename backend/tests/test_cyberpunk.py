"""The Triumvirate (corps forever at war), split cyberware markets, Mama Vex's
gig board, and Juno's clinic (the transformation system's home)."""

import pytest
from app import create_app
from game import corps, data, encounters, fixer, shop
from game.calendar import GameClock
from game.errors import GameError
from game.npc import NPC
from game.player import Player


class FixedRng:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value

    def choice(self, seq):
        return seq[0]


# --- The Triumvirate ---------------------------------------------------------------


def test_three_corps_from_the_same_plant():
    registry = data.load("corps")
    assert set(registry) == {"oceania", "eurasia", "eastasia"}
    for corp in registry.values():
        assert corp["slogan"]
        # Exactly the same at heart: every flagship comes out of Plant 7.
        flagship = data.load("items")[corp["flagship"]]
        assert "Plant 7" in flagship["description"]


def test_the_war_rotates_and_was_always_thus():
    week1 = corps.war_state(1)
    week2 = corps.war_state(2)
    week4 = corps.war_state(4)  # cycle length 3: week 4 == week 1
    assert week1["enemy"] != week2["enemy"]
    assert week1 == week4
    assert "always" in week1["line"].lower()
    # Every corp gets its turn as the eternal enemy.
    assert {corps.war_state(w)["enemy"] for w in (1, 2, 3)} == {
        "oceania",
        "eurasia",
        "eastasia",
    }


def test_travel_can_serve_you_an_ad():
    ad = encounters.roll_encounter({}, set(), rng=FixedRng(0.3), luck=0, week=2)
    # FixedRng picks the first kind... force the ad branch directly instead.
    ad = encounters._corp_ad(data.load("encounters"), 2, FixedRng(0.3))
    assert ad["type"] == "ad"
    assert ad["corp"] in data.load("corps")
    assert "{" not in ad["text"]  # every placeholder was substituted


# --- Two cyberware markets -----------------------------------------------------------


def test_corpo_exchange_is_overpriced_with_exclusives():
    shops = data.load("shops")
    exchange = shops["citadel_ring"]
    assert exchange["price_mod"] > 1.5
    for flagship in ("oceania_panopt", "eurasia_atlas_frame", "eastasia_ghostlace"):
        assert flagship in exchange["stock"]
        # Exclusive: sold nowhere else.
        others = [d for d, s in shops.items() if d != "citadel_ring"]
        assert all(flagship not in shops[d]["stock"] for d in others)


def test_black_market_discounts_used_chrome():
    shops = data.load("shops")
    bazaar = shops["the_grid"]
    assert bazaar["price_mod"] < 0.7
    assert "reflex_splice" in bazaar["stock"]  # used augments, honest prices
    splice = data.load("items")["reflex_splice"]
    black = shop.price(splice, bazaar["price_mod"])
    corpo = shop.price(splice, shops["citadel_ring"]["price_mod"])
    assert black < corpo // 2  # the same chrome, a third the sticker


# --- Black-market cred tiers -----------------------------------------------------------


def _shopper(cred=0):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.location = "the_grid"
    p.street_cred = cred
    p.credits = 5000
    return p


def test_bazaar_tiers_track_the_cred_stages():
    tiers = data.load("shops")["the_grid"]["cred_tiers"]
    assert [t["cred"] for t in tiers] == [10, 40, 100]
    assert [t["name"] for t in tiers] == ["The Back Shelf", "The Locked Case", "The Basement"]
    # Every tier's goods are black-market exclusives: sold in no base stock.
    all_base = {i for s in data.load("shops").values() for i in s["stock"]}
    for tier in tiers:
        assert not all_base.intersection(tier["stock"])


def test_locked_tiers_tease_without_showing_the_goods():
    tiers = shop.tiers("the_grid", cred=0)
    assert all(not t["unlocked"] for t in tiers)
    assert all("stock" not in t and t["tease"] and t["count"] > 0 for t in tiers)
    # At 40 cred the first two rooms open; the Basement still only teases.
    tiers = shop.tiers("the_grid", cred=40)
    assert [t["unlocked"] for t in tiers] == [True, True, False]
    assert any(i["id"] == "flechette_pistol" for i in tiers[1]["stock"])


def test_the_dealer_ignores_nobodies():
    from game.calendar import GameClock

    nobody = _shopper(cred=0)
    with pytest.raises(GameError, match="slide past you.*Back Shelf.*10 cred"):
        shop.buy(nobody, GameClock(), "burner_blade")
    # Something not sold here at ANY cred stays a plain refusal.
    with pytest.raises(GameError, match="isn't sold here"):
        shop.buy(nobody, GameClock(), "prisma_gem")


def test_a_name_opens_the_back_rooms():
    from game.calendar import GameClock

    somebody = _shopper(cred=100)
    result = shop.buy(somebody, GameClock(), "warlord_frame")
    assert result["item"] == "Warlord Frame"
    assert somebody.inventory.get("warlord_frame") == 1


def test_shop_api_reports_tiers(client):
    from game import save

    client.post("/api/travel", json={"to": "the_grid", "mode": "walk"})
    body = client.get("/api/shop").get_json()
    assert [t["unlocked"] for t in body["tiers"]] == [False, False, False]
    assert client.post("/api/shop/buy", json={"item_id": "burner_blade"}).status_code == 400

    save_id, player, clock = save.load_models()
    player.street_cred = 12
    player.credits = 500
    save.save_models(save_id, player, clock)
    body = client.get("/api/shop").get_json()
    assert body["tiers"][0]["unlocked"] is True
    assert any(i["id"] == "burner_blade" for i in body["tiers"][0]["stock"])
    assert client.post("/api/shop/buy", json={"item_id": "burner_blade"}).status_code == 200


# --- Mama Vex & the gig board ---------------------------------------------------------


def _fixer_player(**kw):
    p = Player.create({"name": "Kai", "pronouns": "she/her"})
    p.location = fixer.GIG_DISTRICT
    return p


def test_one_gig_per_day_rotating():
    assert fixer.today_gig(1)["id"] != fixer.today_gig(2)["id"]
    gig_count = len(data.load("gigs"))
    assert fixer.today_gig(1)["id"] == fixer.today_gig(1 + gig_count)["id"]


def test_gig_pays_and_marks_the_day():
    p = _fixer_player()
    clock = GameClock()
    gig = fixer.today_gig(1)
    choice = fixer.run_gig(p, clock, 1, gig["id"], 0)
    assert p.credits == 50 + choice["pay"]
    assert p.last_gig_day == 1
    with pytest.raises(GameError, match="one gig a day"):
        fixer.run_gig(p, clock, 1, gig["id"], 0)


def test_gigs_start_at_vexs_table():
    p = _fixer_player()
    p.location = "the_grid"
    with pytest.raises(GameError, match="Docking Quarter"):
        fixer.run_gig(p, GameClock(), 1, fixer.today_gig(1)["id"], 0)


def test_every_gig_forks_clean_and_dirty():
    for gig in data.load("gigs").values():
        assert len(gig["choices"]) == 2
        clean, dirty = gig["choices"]
        assert dirty["pay"] > clean["pay"]  # the dirty option always pays better
        assert dirty.get("offense"), "the dirty option always costs someone's opinion"


@pytest.fixture
def client():
    app = create_app()
    c = app.test_client()
    c.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    return c


def _to_vex_hours(client):
    # Game starts 08:00; Vex holds court from noon.
    for _ in range(5):
        client.post("/api/action", json={"action": "wait"})


def test_gig_api_applies_the_dirty_fork(client):
    _to_vex_hours(client)
    board = client.get("/api/gigs").get_json()
    assert board["reachable"] is True
    gig = board["gig"]
    dirty = gig["choices"][1]
    before = {c["id"]: c["affection"] for c in client.get("/api/characters").get_json()}
    res = client.post("/api/gig", json={"gig_id": gig["id"], "choice_index": 1})
    assert res.status_code == 200
    body = res.get_json()
    assert body["result"]["pay"] == dirty["pay"]
    after = {c["id"]: c["affection"] for c in client.get("/api/characters").get_json()}
    victim = dirty["offense"]["npc"]
    assert after[victim] < before[victim]  # word travels
    assert client.get("/api/gigs").get_json()["done_today"] is True


# --- Juno & the clinic -----------------------------------------------------------------


def test_vex_and_juno_are_full_cast_members():
    vex, juno = NPC.load("vex"), NPC.load("juno")
    assert vex.romanceable and juno.romanceable
    assert vex.district == "docking_quarter"
    assert juno.district == "the_grid"
    assert vex.schedule and juno.schedule


def test_transformation_lives_at_the_clinic(client):
    from game import save

    save_id, player, clock = save.load_models()
    player.unlocked_transformations = ["pronouns"]
    save.save_models(save_id, player, clock)
    # Wrong district: the clinic gate answers.
    resp = client.post("/api/player/transform", json={"changes": {"pronouns": "he/him"}})
    assert resp.status_code == 400
    assert "second skin" in resp.get_json()["error"].lower()
    # At the clinic it works.
    client.post("/api/travel", json={"to": "the_grid", "mode": "walk"})
    resp = client.post("/api/player/transform", json={"changes": {"pronouns": "he/him"}})
    assert resp.status_code == 200
    assert resp.get_json()["player"]["identity"]["pronouns"] == "he/him"


def test_junos_trust_unlocks_transformation_aspects(client):
    from app import _day_index, _grant_juno_unlocks
    from game import save, social

    save_id, player, clock = save.load_models()
    day = _day_index(clock)
    assert _grant_juno_unlocks(save_id, player, clock) == []  # starting 5: nothing
    social.add_opinion(save_id, "juno", 25, day)  # 5 + 25 = 30
    granted = _grant_juno_unlocks(save_id, player, clock)
    assert set(granted) == {"appearance", "pronouns"}  # 15 and 25 crossed, 40 not
    assert "body" not in player.unlocked_transformations
    social.add_opinion(save_id, "juno", 20, day)  # 50
    assert _grant_juno_unlocks(save_id, player, clock) == ["body"]
