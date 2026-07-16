"""Forget-Me-Not — the Shallows' pawnshop: selling (finally), the shelf that
remembers, buyback at a markup, and the things the shop won't hold."""

import pytest
from app import create_app
from game import data, pawnshop, places
from game.calendar import GameClock
from game.errors import GameError
from game.player import Player


def _player(location="forget_me_not", credits=100):
    p = Player.create({"name": "Kai", "pronouns": "she/her"}, species="Drifter", trait="")
    p.location = location
    p.credits = credits
    return p


# --- The venue -----------------------------------------------------------------


def test_the_shop_keeps_pawnshop_hours():
    assert places.district_of("forget_me_not") == "the_shallows"
    assert places.is_open("forget_me_not", GameClock())  # 08:00
    small_hours = GameClock()
    small_hours.advance(18 * 60)  # 02:00 — the tray is covered, gently
    assert not places.is_open("forget_me_not", small_hours)


# --- Selling ---------------------------------------------------------------------


def test_the_broker_pays_rate_on_the_sticker():
    p, clock = _player(), GameClock()
    p.inventory["first_edition"] = 1  # value 6, rare x8 = 48 sticker
    result = pawnshop.sell(p, clock, "first_edition", day=1)
    assert result["paid"] == round(48 * 0.45)  # 22
    assert p.credits == 100 + 22
    assert "first_edition" not in p.inventory or p.inventory["first_edition"] == 0
    assert p.pawned[0]["item"] == "first_edition"
    assert p.pawned[0]["buyback"] == round(22 * 1.25)  # 28
    assert clock.minute_of_day == 8 * 60 + 10

    with pytest.raises(GameError, match="not carrying"):
        pawnshop.sell(p, clock, "first_edition", day=1)
    away = _player(location="the_shallows")
    with pytest.raises(GameError, match="Forget-Me-Not"):
        pawnshop.sell(away, clock, "protein_cube", day=1)


def test_some_things_the_shop_wont_hold():
    p, clock = _player(), GameClock()
    p.inventory.update({"cyberlink": 1, "archivists_lens": 1, "founders_bell": 1})
    with pytest.raises(GameError, match="EULA"):
        pawnshop.sell(p, clock, "cyberlink", day=1)
    with pytest.raises(GameError, match="habit"):
        pawnshop.sell(p, clock, "archivists_lens", day=1)
    with pytest.raises(GameError, match="shop won't hold"):
        pawnshop.sell(p, clock, "founders_bell", day=1)
    assert p.pawned == [] and p.credits == 100  # nothing moved


def test_offers_cover_the_carriable_and_skip_the_unsellable():
    p = _player()
    p.inventory.update({"tide_glass": 1, "cyberlink": 1})
    quotes = pawnshop.offers(p)
    assert quotes["tide_glass"] == round(60 * 8 * 0.45)  # 216 — the sea provides
    assert "cyberlink" not in quotes
    assert quotes["protein_cube"] >= 1  # cheap, but the broker's fair


# --- The shelf ---------------------------------------------------------------------


def test_buyback_costs_the_markup_and_clears_the_entry():
    p, clock = _player(), GameClock()
    p.inventory["first_edition"] = 1
    pawnshop.sell(p, clock, "first_edition", day=1)
    credits_after_sale = p.credits

    result = pawnshop.buyback(p, clock, 0, day=3)
    assert result["name"] == "First Edition"
    assert p.credits == credits_after_sale - 28
    assert p.inventory["first_edition"] == 1
    assert p.pawned == []

    with pytest.raises(GameError, match="Not on my shelf"):
        pawnshop.buyback(p, clock, 0, day=3)


def test_the_hold_runs_out_and_the_ledger_closes():
    p, clock = _player(), GameClock()
    p.inventory["first_edition"] = 1
    pawnshop.sell(p, clock, "first_edition", day=1)

    assert pawnshop.shelf(p, day=7)[0]["days_left"] == 1  # last call
    assert pawnshop.shelf(p, day=8) == []  # sold on
    assert p.pawned == []
    with pytest.raises(GameError, match="Not on my shelf"):
        pawnshop.buyback(p, clock, 0, day=8)


def test_the_shelf_only_holds_so_much():
    p, clock = _player(credits=0), GameClock()
    cap = data.load("pawnshop")["shelf_cap"]
    p.inventory["protein_cube"] = cap + 3
    for _ in range(cap + 1):
        pawnshop.sell(p, clock, "protein_cube", day=1)
    assert len(p.pawned) == cap  # the oldest got sold on early


# --- Over the API ---------------------------------------------------------------------


def test_pawn_flow_via_api():
    client = create_app().test_client()
    client.post(
        "/api/game/new",
        json={"name": "Kai", "pronouns": "she/her", "species": "Drifter", "trait": ""},
    )
    client.post("/api/travel", json={"to": "the_shallows", "mode": "walk"})
    client.post("/api/travel", json={"to": "forget_me_not", "mode": "walk"})

    board = client.get("/api/pawn").get_json()
    assert board["offers"]["protein_cube"] >= 1
    assert board["shelf"] == []

    res = client.post("/api/pawn/sell", json={"item_id": "protein_cube"})
    assert res.status_code == 200
    assert "counts out your credits" in res.get_json()["pawn"]["line"]

    board = client.get("/api/pawn").get_json()
    assert board["shelf"][0]["item"] == "protein_cube"
    assert board["shelf"][0]["days_left"] == board["hold_days"]

    res = client.post("/api/pawn/buyback", json={"index": 0})
    assert res.status_code == 200
    state = client.get("/api/game/state").get_json()
    assert state["player"]["inventory"]["protein_cube"] == 2  # both cubes home again
