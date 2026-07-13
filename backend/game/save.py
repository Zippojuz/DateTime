"""Persistence for the single autosave. (Milestone 1)

One save row + one player row. Attributes and identity are stored as JSON blobs
so the schema is stable as attributes grow. Multi-slot saves are deferred
(see PLAN.md).
"""

import json

from db import get_connection

from game import social
from game.calendar import GameClock
from game.npc import NPC
from game.player import Player


def create_new_game(identity):
    """Start a fresh game, replacing any existing single save. Returns state."""
    player = Player.create(identity)
    clock = GameClock()
    with get_connection() as conn:
        conn.execute("DELETE FROM player")
        conn.execute("DELETE FROM save")  # cascades to relationships
        cur = conn.execute("INSERT INTO save DEFAULT VALUES")
        save_id = cur.lastrowid
        _insert_player(conn, save_id, player, clock)
        # Seed each relationship at the NPC's starting disposition (neutral by
        # default), so affection begins neutral rather than empty.
        for cid, npc in NPC.load_all().items():
            social.seed_relationship(conn, save_id, cid, npc.starting_disposition)
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
        preferences=json.loads(row["preferences"]),
        location=row["location"],
        credits=row["credits"],
        debt=row["debt"],
        debt_due_week=row["debt_due_week"],
        fired_events=json.loads(row["fired_events"]),
        inventory=json.loads(row["inventory"]),
        combat_level=row["combat_level"],
        combat_xp=row["combat_xp"],
        difficulty=row["difficulty"],
        max_floor=row["max_floor"],
        dungeon=json.loads(row["dungeon"]),
        combat=json.loads(row["combat"]),
        equipment=json.loads(row["equipment"]),
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
                   species=?, attributes=?, preferences=?, energy=?,
                   location=?, credits=?, debt=?, debt_due_week=?, fired_events=?,
                   inventory=?,
                   combat_level=?, combat_xp=?, difficulty=?, max_floor=?,
                   dungeon=?, combat=?, equipment=?,
                   created_identity=?, current_identity=?, unlocked_transformations=?,
                   clock_week=?, clock_day=?, clock_minute=?
               WHERE save_id=?""",
            (
                player.species,
                json.dumps(player.attributes),
                json.dumps(player.preferences),
                player.energy,
                player.location,
                player.credits,
                player.debt,
                player.debt_due_week,
                json.dumps(player.fired_events),
                json.dumps(player.inventory),
                player.combat_level,
                player.combat_xp,
                player.difficulty,
                player.max_floor,
                json.dumps(player.dungeon),
                json.dumps(player.combat),
                json.dumps(player.equipment),
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
               save_id, species, attributes, preferences, energy,
               location, credits, debt, debt_due_week, fired_events, inventory,
               combat_level, combat_xp, difficulty, max_floor, dungeon, combat, equipment,
               created_identity, current_identity, unlocked_transformations,
               clock_week, clock_day, clock_minute)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            save_id,
            player.species,
            json.dumps(player.attributes),
            json.dumps(player.preferences),
            player.energy,
            player.location,
            player.credits,
            player.debt,
            player.debt_due_week,
            json.dumps(player.fired_events),
            json.dumps(player.inventory),
            player.combat_level,
            player.combat_xp,
            player.difficulty,
            player.max_floor,
            json.dumps(player.dungeon),
            json.dumps(player.combat),
            json.dumps(player.equipment),
            json.dumps(player.created_identity),
            json.dumps(player.current_identity),
            json.dumps(player.unlocked_transformations),
            clock.week,
            clock.day,
            clock.minute_of_day,
        ),
    )
