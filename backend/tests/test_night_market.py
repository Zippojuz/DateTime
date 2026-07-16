"""The Night Market (first night-only venue: rotating stalls, street food,
gossip), hovercabs + the Loop, and homes: everyone goes somewhere off-hours."""

import pytest
from app import create_app
from game import data, places, shop, world
from game.calendar import GameClock
from game.errors import GameError
from game.npc import NPC
from game.player import Player


def _player(location="night_market", credits=500):
    p = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Drifter", trait="")
    p.location = location
    p.credits = credits
    return p


def _night():
    clock = GameClock()
    clock.advance(12 * 60)  # 20:00 — stalls in full swing
    return clock


# --- The venue -----------------------------------------------------------------------


def test_the_market_blooms_at_dusk():
    assert places.district_of("night_market") == "bloom_district"
    assert not places.is_open("night_market", GameClock())  # 08:00: chalk outlines
    assert places.is_open("night_market", _night())
    small_hours = GameClock()
    small_hours.advance(18 * 60)  # 02:00 — still going
    assert places.is_open("night_market", small_hours)


# --- Rotating stalls -------------------------------------------------------------------


def test_stalls_rotate_nightly_and_deterministically():
    market = data.load("shops")["night_market"]
    tonight = shop.rotating_ids(market, day=3)
    assert len(tonight) == market["rotates"]["count"]
    assert tonight == shop.rotating_ids(market, day=3)  # same night, same stalls
    different = {tuple(shop.rotating_ids(market, day=d)) for d in range(1, 15)}
    assert len(different) > 1  # the market changes
    assert shop.rotating_ids(market, day=None) == []  # no day, no stalls


def test_stock_flags_tonights_stalls():
    listed = shop.stock("night_market", day=5)
    flagged = [i["id"] for i in listed if i.get("tonight")]
    assert flagged == shop.rotating_ids(data.load("shops")["night_market"], day=5)
    base = [i["id"] for i in listed if not i.get("tonight")]
    assert "skewered_something" in base and "glow_broth" in base


def test_tonights_find_is_buyable_but_not_last_weeks():
    market = data.load("shops")["night_market"]
    clock = _night()
    day = (clock.week - 1) * 7 + clock.day
    tonight = shop.rotating_ids(market, day)
    missing = next(i for i in market["rotates"]["pool"] if i not in tonight)
    p = _player()
    bought = shop.buy(p, clock, tonight[0])
    assert p.inventory.get(tonight[0]) == 1
    assert bought["cost"] > 0
    with pytest.raises(GameError, match="isn't sold here"):
        shop.buy(p, clock, missing)


def test_street_food_feeds_you():
    from game import inventory

    p = _player()
    p.energy = 40
    inventory.add_item(p, "glow_broth", 1)
    result = inventory.use_item(p, "glow_broth")
    assert result["energy"] == 30
    assert p.energy == 70


# --- Cabs + the Loop ---------------------------------------------------------------------


def test_cabs_fly_door_to_door_at_a_flat_rate():
    # Cross-city, straight to a venue door, one price, six minutes.
    p = _player("docking_quarter")
    cost = world.travel(p, _night(), "night_market", "cab")
    assert cost == {"distance": "cab", "minutes": 6, "energy": -2, "credits": 30}
    assert p.location == "night_market"
    assert p.credits == 470


def test_priced_in_covers_the_loop_but_never_cabs():
    suit = Player.create({"name": "Kai", "pronouns": "she/her"}, trait="human")  # Priced In
    suit.location = "docking_quarter"
    suit.credits = 100
    world.travel(suit, GameClock(), "the_grid", "transit")
    assert suit.credits == 100  # the Loop reads their face
    world.travel(suit, GameClock(), "docking_quarter", "cab")
    assert suit.credits == 70  # the cab does not


def test_cab_costs_are_gated_by_credits():
    broke = _player("docking_quarter", credits=10)
    with pytest.raises(GameError, match="credits"):
        world.travel(broke, _night(), "bloom_district", "cab")


# --- Gossip -------------------------------------------------------------------------------


@pytest.fixture
def client():
    c = create_app().test_client()
    c.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Drifter", "trait": ""},
    )
    return c


def _to_market(client):
    for _ in range(10):  # 08:00 -> 18:00
        client.post("/api/action", json={"action": "wait"})
    return client.post("/api/travel", json={"to": "night_market", "mode": "cab"})


def test_gossip_hints_once_a_night(client):
    # Closed by day — and you have to actually be there.
    resp = client.post("/api/market/gossip")
    assert resp.status_code == 400
    assert _to_market(client).status_code == 200
    body = client.get("/api/shop").get_json()
    assert body["gossip_available"] is True
    assert any(i.get("tonight") for i in body["stock"])

    res = client.post("/api/market/gossip")
    assert res.status_code == 200
    rumor = res.get_json()
    assert rumor["npc"] and rumor["topic"]
    assert rumor["npc"] in rumor["text"]
    # A rumor, not a fact: nothing is marked discovered.
    cast = {c["id"]: c for c in client.get("/api/characters").get_json()}
    assert all(not c["preferences"] for c in cast.values())
    # Once a night.
    assert client.post("/api/market/gossip").status_code == 400
    assert client.get("/api/shop").get_json()["gossip_available"] is False


def test_gossip_rumors_are_true(client):
    _to_market(client)
    rumor = client.post("/api/market/gossip").get_json()
    npc = next(n for n in NPC.load_all().values() if n.name == rumor["npc"])
    topics = data.load("topics")
    topic_id = next(t for t, spec in topics.items() if spec["name"] == rumor["topic"])
    sentiment = npc.preferences[topic_id]["sentiment"]
    if "soft on" in rumor["text"]:
        assert sentiment in ("love", "like")
    else:
        assert sentiment in ("dislike", "hate")


# --- Homes: full schedules, everyone goes somewhere ----------------------------------------


def test_everyone_has_a_home():
    for cid, npc in NPC.load_all().items():
        assert npc.home.get("name") and npc.home.get("blurb"), f"{cid} is unhoused"


def test_schedules_cover_every_minute_of_the_day():
    def to_min(hhmm):
        h, m = hhmm.split(":")
        return int(h) * 60 + int(m)

    for cid, npc in NPC.load_all().items():
        covered = [False] * (24 * 60)
        for window in npc.schedule:
            start, end = to_min(window["start"]), to_min(window["end"])
            span = range(start, end) if start <= end else [*range(start, 1440), *range(0, end)]
            for minute in span:
                covered[minute] = True
        gaps = sum(1 for m in covered if not m)
        assert gaps == 0, f"{cid}'s schedule has {gaps} unaccounted minutes"


def test_availability_reports_activity_and_home():
    small_hours = GameClock()
    small_hours.advance(20 * 60)  # 04:00 — Vex is unreachable, on purpose
    avail = world.availability(NPC.load("vex"), small_hours)
    assert avail["available"] is False
    assert avail["location"] == "home"
    assert avail["activity"] == "Unreachable, on purpose"


def test_nyx_haunts_the_night_market():
    evening = GameClock()
    evening.advance(11 * 60)  # 19:00
    avail = world.availability(NPC.load("nyx"), evening)
    assert avail["available"] is True
    assert avail["district"] == "night_market"
