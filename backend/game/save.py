"""Persistence for the single autosave. (Milestone 1)

One save row + one player row. Attributes and identity are stored as JSON blobs
so the schema is stable as attributes grow. Multi-slot saves are deferred
(see PLAN.md).
"""

import json

from db import get_connection
from game.calendar import GameClock
from game.player import Player


def create_new_game(identity):
    """Start a fresh game, replacing any existing single save. Returns state."""
    player = Player.create(identity)
    clock = GameClock()
    with get_connection() as conn:
        conn.execute("DELETE FROM player")
        conn.execute("DELETE FROM save")
        cur = conn.execute("INSERT INTO save DEFAULT VALUES")
        _insert_player(conn, cur.lastrowid, player, clock)
    return state_dict(player, clock)


def load_models():
    """Return (save_id, Player, GameClock) for the current save, or None."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM player LIMIT 1").fetchone()
    if row is None:
        return None
    player = Player(
        identity=json.loads(row["current_identity"]),
        species=row["species"],
        attributes=json.loads(row["attributes"]),
        energy=row["energy"],
        created_identity=json.loads(row["created_identity"]),
        unlocked_transformations=json.loads(row["unlocked_transformations"]),
    )
    clock = GameClock(
        week=row["clock_week"],
        day=row["clock_day"],
        minute_of_day=row["clock_minute"],
    )
    return row["save_id"], player, clock


def get_state():
    """Return the current save's state dict, or None if no game is in progress."""
    models = load_models()
    if models is None:
        return None
    _, player, clock = models
    return state_dict(player, clock)


def save_models(save_id, player, clock):
    with get_connection() as conn:
        conn.execute(
            """UPDATE player SET
                   species=?, attributes=?, energy=?,
                   created_identity=?, current_identity=?, unlocked_transformations=?,
                   clock_week=?, clock_day=?, clock_minute=?
               WHERE save_id=?""",
            (
                player.species,
                json.dumps(player.attributes),
                player.energy,
                json.dumps(player.created_identity),
                json.dumps(player.current_identity),
                json.dumps(player.unlocked_transformations),
                clock.week,
                clock.day,
                clock.minute_of_day,
                save_id,
            ),
        )


def state_dict(player, clock):
    return {"player": player.to_dict(), "clock": clock.to_dict()}


def _insert_player(conn, save_id, player, clock):
    conn.execute(
        """INSERT INTO player (
               save_id, species, attributes, energy,
               created_identity, current_identity, unlocked_transformations,
               clock_week, clock_day, clock_minute)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            save_id,
            player.species,
            json.dumps(player.attributes),
            player.energy,
            json.dumps(player.created_identity),
            json.dumps(player.current_identity),
            json.dumps(player.unlocked_transformations),
            clock.week,
            clock.day,
            clock.minute_of_day,
        ),
    )
