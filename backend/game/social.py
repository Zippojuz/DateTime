"""Relationships and affection. (Milestone 2)

Affection is a per-NPC value on the save (0–100). Because dialogue is free (no
time cost in M2), a per-day gate (`last_talked_day`) prevents re-talking the
same NPC repeatedly to farm affection. Never gates on player identity — see
game/player.py identity policy.
"""

from db import get_connection

MAX_AFFECTION = 100
MIN_AFFECTION = 0


def get_affection(save_id, npc_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT affection FROM relationships WHERE save_id=? AND npc_id=?",
            (save_id, npc_id),
        ).fetchone()
    return row["affection"] if row else 0


def add_affection(save_id, npc_id, delta):
    """Add (clamped) affection, creating the relationship row if needed.
    Returns the new value."""
    new_value = max(MIN_AFFECTION, min(MAX_AFFECTION, get_affection(save_id, npc_id) + delta))
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO relationships (save_id, npc_id, affection)
                   VALUES (?, ?, ?)
               ON CONFLICT(save_id, npc_id) DO UPDATE SET affection=excluded.affection""",
            (save_id, npc_id, new_value),
        )
    return new_value


def has_talked_today(save_id, npc_id, day_index):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT last_talked_day FROM relationships WHERE save_id=? AND npc_id=?",
            (save_id, npc_id),
        ).fetchone()
    return bool(row) and row["last_talked_day"] == day_index


def mark_talked(save_id, npc_id, day_index):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO relationships (save_id, npc_id, last_talked_day)
                   VALUES (?, ?, ?)
               ON CONFLICT(save_id, npc_id)
                   DO UPDATE SET last_talked_day=excluded.last_talked_day""",
            (save_id, npc_id, day_index),
        )


def all_relationships(save_id):
    """Return {npc_id: {affection, last_talked_day}} for the save."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT npc_id, affection, last_talked_day FROM relationships WHERE save_id=?",
            (save_id,),
        ).fetchall()
    return {
        r["npc_id"]: {"affection": r["affection"], "last_talked_day": r["last_talked_day"]}
        for r in rows
    }
