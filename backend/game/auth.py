"""Accounts — username + password, sessions via flask-login.

Deliberately minimal: no email, no resets, no profiles. A username is an
identity for the *save*, not the character (characters have their own names,
pronouns, species — see the design doc). The first account ever registered
becomes the admin; everyone after is a player unless an admin says otherwise.
"""

from db import get_connection
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from game.errors import GameError

USERNAME_MIN, USERNAME_MAX = 2, 24
PASSWORD_MIN = 6


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.is_admin = bool(row["is_admin"])


def _row(where, params):
    with get_connection() as conn:
        return conn.execute(f"SELECT * FROM users WHERE {where}", params).fetchone()


def load_user(user_id):
    """flask-login's user_loader."""
    row = _row("id=?", (user_id,))
    return User(row) if row else None


def register(username, password):
    """Create an account (the first one ever is the admin). Returns the User."""
    username = (username or "").strip()
    password = password or ""
    if not (USERNAME_MIN <= len(username) <= USERNAME_MAX):
        raise GameError(f"Usernames run {USERNAME_MIN}–{USERNAME_MAX} characters.")
    if len(password) < PASSWORD_MIN:
        raise GameError(f"Passwords need at least {PASSWORD_MIN} characters.")
    if _row("username=?", (username,)):
        raise GameError("That name's taken. The city is full of people.")

    with get_connection() as conn:
        first = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), 1 if first else 0),
        )
        user_id = cur.lastrowid
    return load_user(user_id)


def login(username, password):
    """Check credentials. Returns the User or raises."""
    row = _row("username=?", ((username or "").strip(),))
    if row is None or not check_password_hash(row["password_hash"], password or ""):
        raise GameError("Wrong name or password. The door stays shut.")
    with get_connection() as conn:
        conn.execute("UPDATE users SET last_seen=datetime('now') WHERE id=?", (row["id"],))
    return User(row)


def all_users():
    """Every account, for the admin roster."""
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users ORDER BY id").fetchall()


def delete_user(user_id):
    """Remove an account and everything it owns (save cascades relationships)."""
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM save WHERE user_id=?", (user_id,)).fetchone()
        if row:
            conn.execute("DELETE FROM player WHERE save_id=?", (row["id"],))
            conn.execute("DELETE FROM save WHERE id=?", (row["id"],))
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
