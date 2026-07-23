"""A place to live. (Milestone: Housing)

Home is where you sleep — and, uniquely, the *only* place a full night's Rest
restores you. Away from home you can only catnap (see game/actions.py). A home
also carries a stash (an item chest kept off your person), a perk that feeds
the shared effect vocabulary (train_bonus, luck_bonus, gift_affection_bonus,
research_topics_bonus, …), and — once it can host — the setting for home dates.

Two ways to hold a place (data/homes.json):
- **Rent** — cheap to move into, a weekly credit drain settled on the week
  rollover; miss it and you're evicted back to the ship's berth.
- **Buy** — a lump sum, owned forever, no drain. The aspiration.

'berth' is your ship's fold-down bunk: free, always owned, and a poor sleep —
the fallback you can never lose, so you can always bed down somewhere.
"""

from game import data
from game.errors import GameError

BERTH = "berth"


def homes():
    return data.load("homes")


def get(home_id):
    return homes().get(home_id)


def current(player):
    """The player's current residence (falls back to the berth)."""
    return homes().get(player.home) or homes()[BERTH]


# --- Perk resolution --------------------------------------------------------
# Your current home's perk contributes to the same effect vocabulary as species
# traits, tea, and courses. You only get the perk of the home you live in.


def _effects(player):
    return current(player).get("perk") or {}


def bonus(player, key, default=0):
    """An additive home-perk effect (0 if the current home doesn't grant it)."""
    return default + _effects(player).get(key, 0)


def mult(player, key, default=1.0):
    """A multiplicative home-perk effect (1.0 if not granted)."""
    return default * _effects(player).get(key, 1.0)


# --- Rest -------------------------------------------------------------------


def is_home(player):
    """True when the player is standing in their current residence."""
    return player.location == player.home


def rest_minutes(player):
    """How long a full night's sleep takes here — nicer homes rest faster, so
    less of the day is burned. Only meaningful when the player is home."""
    return current(player).get("rest_minutes", 480)


def require_home_to_sleep(player):
    """Guard for the Rest action: you can only bed down in your own place."""
    if not is_home(player):
        home = current(player)
        raise GameError(
            f"You can only bed down at home — {home['name']}. "
            "Head there to sleep (a catnap is the best you'll manage out here)."
        )


# --- Rent settlement --------------------------------------------------------


def settle_rent(player, clock):
    """Charge any weeks of rent owed since it was last settled. Called at
    natural touchpoints (sleeping, checking listings). Evicts to the berth if
    the player can't cover it. Returns a dict describing what happened, or None
    when nothing was due (owned home, berth, or already paid up)."""
    home = current(player)
    rent = home.get("rent", 0)
    # No drain on the berth, free places, or a home you own outright — owning
    # it is exactly what stops the rent clock, even though the listing still
    # quotes a rent for people who'd rather lease it.
    if home["id"] == BERTH or rent <= 0 or home["id"] in player.owned_homes:
        return None
    weeks_owed = clock.week - player.rent_paid_week
    if weeks_owed <= 0:
        return None
    due = rent * weeks_owed
    if player.credits >= due:
        player.credits -= due
        player.rent_paid_week = clock.week
        return {"paid": due, "weeks": weeks_owed, "home": home["name"], "evicted": False}
    # Can't cover it — evicted back to the berth (nothing charged).
    evicted_from = home["name"]
    player.home = BERTH
    player.rent_paid_week = 0
    if player.location == home["id"]:
        player.location = home["district"]
    return {"paid": 0, "weeks": weeks_owed, "home": evicted_from, "evicted": True}


# --- Acquisition ------------------------------------------------------------


def _owned(player, home_id):
    return home_id == BERTH or home_id in player.owned_homes


def rent(player, clock, home_id):
    """Move into a place as a renter: pay the first week now, and you live
    there until the weekly rent lapses. Returns a result dict."""
    home = homes().get(home_id)
    if not home:
        raise GameError("No such place.")
    if home["id"] == BERTH:
        raise GameError("The berth is yours already — it's your ship.")
    if home["rent"] <= 0:
        raise GameError("That place is for sale, not for rent.")
    if player.home == home_id:
        raise GameError("You already live there.")
    if player.credits < home["rent"]:
        raise GameError(f"First week's rent is {home['rent']} credits — you're short.")
    # Settle any drain on the place you're leaving before you go.
    settle_rent(player, clock)
    player.credits -= home["rent"]
    player.home = home_id
    player.rent_paid_week = clock.week
    return {"home": home["name"], "moved_in": True, "paid": home["rent"], "owned": False}


def buy(player, clock, home_id):
    """Buy a place outright: a lump sum, owned forever, no weekly drain. You
    move in on purchase. Returns a result dict."""
    home = homes().get(home_id)
    if not home:
        raise GameError("No such place.")
    if home["id"] == BERTH:
        raise GameError("You can't buy your own ship's bunk.")
    if home["price"] <= 0:
        raise GameError("That place isn't for sale.")
    if home_id in player.owned_homes:
        raise GameError("You already own that.")
    if player.credits < home["price"]:
        raise GameError(f"That's {home['price']} credits — you can't cover it.")
    settle_rent(player, clock)
    player.credits -= home["price"]
    player.owned_homes.append(home_id)
    player.home = home_id
    player.rent_paid_week = 0  # owned: no drain
    return {"home": home["name"], "moved_in": True, "paid": home["price"], "owned": True}


def move_in(player, home_id):
    """Switch your current residence to a home you already own (no cost). Handy
    once you hold more than one deed."""
    if not _owned(player, home_id):
        raise GameError("You don't own that place.")
    player.home = home_id
    player.rent_paid_week = 0
    return {"home": current(player)["name"], "moved_in": True}


# --- Listings ---------------------------------------------------------------


def _status(player, home):
    """Per-home flags for the listings board."""
    hid = home["id"]
    owned = hid in player.owned_homes
    return {
        "current": player.home == hid,
        "owned": owned or hid == BERTH,
        "can_rent": (home["rent"] > 0 and player.home != hid and player.credits >= home["rent"]),
        "can_buy": (home["price"] > 0 and not owned and player.credits >= home["price"]),
    }


def listings(player, clock):
    """The housing board: every home with cost, perk, and per-home status,
    plus the current residence. Settles any rent owed first."""
    rent_event = settle_rent(player, clock)
    rows = []
    for home in sorted(homes().values(), key=lambda h: h["tier"]):
        rows.append(
            {
                "id": home["id"],
                "name": home["name"],
                "district": home["district"],
                "tier": home["tier"],
                "rent": home["rent"],
                "price": home["price"],
                "rest_minutes": home["rest_minutes"],
                "stash": home["stash"],
                "host": home["host"],
                "perk": dict(home.get("perk") or {}),
                "vibe": home["vibe"],
                "tagline": home.get("tagline", ""),
                **_status(player, home),
            }
        )
    home = current(player)
    return {
        "homes": rows,
        "current": home["id"],
        "current_name": home["name"],
        "at_home": is_home(player),
        "rent_paid_week": player.rent_paid_week,
        "rent_event": rent_event,
    }


# --- Stash ------------------------------------------------------------------


def stash_capacity(player):
    return current(player).get("stash", 0)


def _stash_used(player):
    return sum(player.stash.values())


def stash_deposit(player, item_id, qty=1):
    """Move an item from your pack into the home stash (must be home)."""
    require_home_to_sleep(player)  # same rule: you can only reach your own stash
    cap = stash_capacity(player)
    if cap <= 0:
        raise GameError("This place has nowhere to stash anything.")
    if player.inventory.get(item_id, 0) < qty:
        raise GameError("You're not carrying that.")
    if _stash_used(player) + qty > cap:
        raise GameError("The stash is full.")
    player.inventory[item_id] -= qty
    if player.inventory[item_id] <= 0:
        del player.inventory[item_id]
    player.stash[item_id] = player.stash.get(item_id, 0) + qty
    return {"item": item_id, "qty": qty, "used": _stash_used(player), "capacity": cap}


def stash_withdraw(player, item_id, qty=1):
    """Move an item from the home stash back into your pack (must be home)."""
    require_home_to_sleep(player)
    if player.stash.get(item_id, 0) < qty:
        raise GameError("That's not in the stash.")
    player.stash[item_id] -= qty
    if player.stash[item_id] <= 0:
        del player.stash[item_id]
    player.inventory[item_id] = player.inventory.get(item_id, 0) + qty
    return {
        "item": item_id,
        "qty": qty,
        "used": _stash_used(player),
        "capacity": stash_capacity(player),
    }


# --- Travel gating ----------------------------------------------------------


def is_home_place(place_id):
    """Whether a place id names a residence (rather than a district/venue)."""
    return place_id in homes()


def can_enter(player, place_id):
    """You may only step into your *own* current home — not other people's, and
    not places you've rented in the past and left."""
    return place_id == player.home
