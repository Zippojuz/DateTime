"""Accounts and the admin desk: registration, sessions, per-user saves
(nobody deletes a stranger's city anymore), and the admin player tools."""

from app import create_app


def _client():
    c = create_app().test_client()
    c.no_auto_login = True  # these tests exercise the real flow
    return c


def _register(c, username, password="hunter22"):
    return c.post("/api/auth/register", json={"username": username, "password": password})


# --- The door ---------------------------------------------------------------


def test_the_city_needs_a_name_for_the_tab():
    c = _client()
    res = c.get("/api/game/state")
    assert res.status_code == 401
    assert "Log in first" in res.get_json()["error"]
    # Content registries stay public — the title screen renders before login.
    assert c.get("/api/species").status_code == 200
    assert c.get("/api/venues").status_code == 200
    assert c.get("/api/corps").status_code == 200


def test_register_login_logout_me():
    c = _client()
    assert _register(c, "wren").status_code == 201
    me = c.get("/api/auth/me").get_json()
    assert me["username"] == "wren"

    c.post("/api/auth/logout")
    assert c.get("/api/auth/me").status_code == 401
    assert (
        c.post("/api/auth/login", json={"username": "wren", "password": "wrong"}).status_code == 401
    )
    assert (
        c.post("/api/auth/login", json={"username": "wren", "password": "hunter22"}).status_code
        == 200
    )


def test_registration_has_standards():
    c = _client()
    assert _register(c, "x").status_code == 400  # too short
    assert _register(c, "wren2", password="tiny").status_code == 400
    _register(c, "taken")
    res = _register(c, "TAKEN")  # case-insensitive collision
    assert res.status_code == 400
    assert "taken" in res.get_json()["error"].lower()


# --- Saves belong to accounts ---------------------------------------------------


def test_two_players_two_cities():
    alice, bob = _client(), _client()
    _register(alice, "alice")
    _register(bob, "bob")

    alice.post("/api/game/new", json={"name": "Kai", "pronouns": "she/her"})
    bob.post("/api/game/new", json={"name": "Rook", "pronouns": "he/him"})

    # Bob starting a game did NOT delete Alice's city (it used to).
    assert alice.get("/api/game/state").get_json()["player"]["identity"]["name"] == "Kai"
    assert bob.get("/api/game/state").get_json()["player"]["identity"]["name"] == "Rook"

    # And their days diverge independently.
    alice.post("/api/action", json={"action": "wait"})
    assert alice.get("/api/game/state").get_json()["clock"]["time"] == "09:00"
    assert bob.get("/api/game/state").get_json()["clock"]["time"] == "08:00"


# --- The admin desk ---------------------------------------------------------------


def _promote(username):
    """Make an account an admin directly (tests share a DB, so the 'first
    account ever' seat is taken by whichever test ran first)."""
    from db import get_connection

    with get_connection() as conn:
        conn.execute("UPDATE users SET is_admin=1 WHERE username=?", (username,))


def test_first_account_is_the_admin_and_gates_hold():
    from game import auth

    users = auth.all_users()
    # The very first account in the database holds the admin seat...
    assert bool(users[0]["is_admin"]) is True
    # ...and a brand-new one doesn't.
    player = _client()
    fresh = _register(player, "regular").get_json()
    assert fresh["is_admin"] is False
    assert player.get("/api/admin/players").status_code == 403


def test_admin_manages_players():
    admin, player = _client(), _client()
    _register(admin, "boss")
    _promote("boss")
    _register(player, "stuck_sam")
    player.post("/api/game/new", json={"name": "Sam", "pronouns": "they/them"})

    roster = admin.get("/api/admin/players").get_json()
    sam = next(r for r in roster if r["username"] == "stuck_sam")
    assert sam["save"]["name"] == "Sam"
    assert sam["save"]["credits"] == 50

    # Comp credits.
    res = admin.post(f"/api/admin/players/{sam['user_id']}/comp", json={"credits": 500})
    assert res.get_json()["credits"] == 550

    # Unstick: home, rested, no lingering scene state.
    player.post("/api/travel", json={"to": "the_grid", "mode": "walk"})
    admin.post(f"/api/admin/players/{sam['user_id']}/unstick")
    state = player.get("/api/game/state").get_json()
    assert state["player"]["location"] == "docking_quarter"
    assert state["player"]["energy"] == 100

    # Inspect + delete (but never yourself).
    assert admin.get(f"/api/admin/players/{sam['user_id']}").status_code == 200
    me = next(r for r in admin.get("/api/admin/players").get_json() if r["username"] == "boss")
    assert admin.delete(f"/api/admin/players/{me['user_id']}").status_code == 400
    assert admin.delete(f"/api/admin/players/{sam['user_id']}").status_code == 200
    assert player.get("/api/game/state").status_code == 401  # session user is gone
