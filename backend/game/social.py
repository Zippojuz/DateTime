"""Relationships, affection, memory, and discovered knowledge. (Milestone 2 / 3)

Affection is NOT a flat number — it is DERIVED from a memory log so it can decay
like real life:

- Each relationship starts at a neutral (or per-NPC) `starting_disposition`.
- Every affection change is recorded as a memory event {day, delta, decays,
  severity}.
- Positive events and standing incompatibilities are permanent (never decay).
- Offenses decay toward zero over a window set by severity — minor fades fast,
  moderate slowly, severe never.
- Offenses hit HARDER when the relationship is weak/early: the recorded penalty
  is amplified (up to 2x at neutral, down to 1x when close). So an early rudeness
  scars more than the same act once you're trusted.

effective affection(today) = clamp(starting_disposition + Σ value(event, today)).

Discovered knowledge is tracked per relationship: which of the NPC's preferences
the player has learned, and which of the player's the NPC has learned. Nobody
reacts to a preference they don't know about. Never gates on player identity.
"""

import json

from db import get_connection

MAX_AFFECTION = 100
MIN_AFFECTION = -100
NEUTRAL_AFFECTION = 0

# How long (in-game days) an offense takes to fully fade. Severe never fades.
DECAY_DAYS = {"minor": 7, "moderate": 30}

# Amplification of an offense at neutral affection; tapers to 1.0 as affection
# approaches MAX. "Hits harder early."
MAX_EARLY_AMPLIFICATION = 2.0


# --- Seeding & raw row access ----------------------------------------------


def seed_relationship(conn, save_id, npc_id, starting_disposition=0):
    """Create the relationship row at its starting disposition (called on new
    game, within the caller's transaction)."""
    conn.execute(
        """INSERT OR IGNORE INTO relationships (save_id, npc_id, starting_disposition)
               VALUES (?, ?, ?)""",
        (save_id, npc_id, starting_disposition),
    )


def ensure_relationship(save_id, npc_id, starting_disposition=0):
    """Seed a relationship row mid-game if it doesn't exist yet (used when an
    NPC unlocks after game start — e.g. a defeated deep-floor boss surfacing)."""
    with get_connection() as conn:
        seed_relationship(conn, save_id, npc_id, starting_disposition)


def _row(save_id, npc_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM relationships WHERE save_id=? AND npc_id=?",
            (save_id, npc_id),
        ).fetchone()


# --- Affection (derived from the memory log) --------------------------------


def _event_value(event, today):
    delta = event["delta"]
    if not event.get("decays"):
        return delta
    window = DECAY_DAYS.get(event.get("severity", "minor"), 7)
    elapsed = max(0, today - event["day"])
    if elapsed >= window:
        return 0
    return round(delta * (1 - elapsed / window))


def _affection_from(starting_disposition, memories, today):
    total = starting_disposition + sum(_event_value(m, today) for m in memories)
    return max(MIN_AFFECTION, min(MAX_AFFECTION, total))


def get_affection(save_id, npc_id, today):
    row = _row(save_id, npc_id)
    if row is None:
        return NEUTRAL_AFFECTION
    return _affection_from(row["starting_disposition"], json.loads(row["memories"]), today)


def _append_memory(save_id, npc_id, event):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT memories FROM relationships WHERE save_id=? AND npc_id=?",
            (save_id, npc_id),
        ).fetchone()
        memories = json.loads(row["memories"]) if row else []
        memories.append(event)
        conn.execute(
            """INSERT INTO relationships (save_id, npc_id, memories)
                   VALUES (?, ?, ?)
               ON CONFLICT(save_id, npc_id) DO UPDATE SET memories=excluded.memories""",
            (save_id, npc_id, json.dumps(memories)),
        )


def add_opinion(save_id, npc_id, delta, today):
    """Record a permanent affection change (positive gains, standing
    compatibility). Never decays. Returns the new effective affection."""
    if delta:
        _append_memory(save_id, npc_id, {"day": today, "delta": delta, "decays": False})
    return get_affection(save_id, npc_id, today)


def record_offense(save_id, npc_id, base_delta, today, severity="minor"):
    """Record a negative action. Amplified when the bond is weak; decays over a
    severity-based window (severe never decays). Returns new effective affection."""
    current = get_affection(save_id, npc_id, today)
    trust = max(0, min(MAX_AFFECTION, current)) / MAX_AFFECTION  # 0 at neutral/low, 1 near max
    amplification = MAX_EARLY_AMPLIFICATION - (MAX_EARLY_AMPLIFICATION - 1.0) * trust
    delta = round(base_delta * amplification)
    _append_memory(
        save_id,
        npc_id,
        {"day": today, "delta": delta, "decays": severity != "severe", "severity": severity},
    )
    return get_affection(save_id, npc_id, today)


# --- Per-day conversation gate ---------------------------------------------


def has_talked_today(save_id, npc_id, day_index):
    row = _row(save_id, npc_id)
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


def has_messaged_today(save_id, npc_id, day_index):
    row = _row(save_id, npc_id)
    return bool(row) and row["last_message_day"] == day_index


def mark_messaged(save_id, npc_id, day_index):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO relationships (save_id, npc_id, last_message_day)
                   VALUES (?, ?, ?)
               ON CONFLICT(save_id, npc_id)
                   DO UPDATE SET last_message_day=excluded.last_message_day""",
            (save_id, npc_id, day_index),
        )


def has_dated_this_week(save_id, npc_id, week):
    row = _row(save_id, npc_id)
    return bool(row) and row["last_date_week"] == week


def mark_dated(save_id, npc_id, week):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO relationships (save_id, npc_id, last_date_week)
                   VALUES (?, ?, ?)
               ON CONFLICT(save_id, npc_id)
                   DO UPDATE SET last_date_week=excluded.last_date_week""",
            (save_id, npc_id, week),
        )


def has_gifted_today(save_id, npc_id, day_index):
    row = _row(save_id, npc_id)
    return bool(row) and row["last_gift_day"] == day_index


def mark_gifted(save_id, npc_id, day_index):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO relationships (save_id, npc_id, last_gift_day)
                   VALUES (?, ?, ?)
               ON CONFLICT(save_id, npc_id)
                   DO UPDATE SET last_gift_day=excluded.last_gift_day""",
            (save_id, npc_id, day_index),
        )


# Coarse relationship stage from affection, for UI labels.
def stage(affection):
    if affection >= 50:
        return "close"
    if affection >= 25:
        return "friend"
    if affection >= 10:
        return "acquaintance"
    if affection <= -25:
        return "hostile"
    return "stranger"


# --- Discovered knowledge ---------------------------------------------------


def _add_to_list_column(save_id, npc_id, column, value):
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT {column} FROM relationships WHERE save_id=? AND npc_id=?",
            (save_id, npc_id),
        ).fetchone()
        current = json.loads(row[column]) if row else []
        if value in current:
            return
        current.append(value)
        conn.execute(
            f"""INSERT INTO relationships (save_id, npc_id, {column})
                    VALUES (?, ?, ?)
                ON CONFLICT(save_id, npc_id) DO UPDATE SET {column}=excluded.{column}""",
            (save_id, npc_id, json.dumps(current)),
        )


def discover_npc_topic(save_id, npc_id, topic):
    """The player learns the NPC's stance on a topic."""
    _add_to_list_column(save_id, npc_id, "known_npc_topics", topic)


def reveal_player_topic(save_id, npc_id, topic):
    """The NPC learns the player's stance on a topic."""
    _add_to_list_column(save_id, npc_id, "known_player_topics", topic)


def get_known_npc_topics(save_id, npc_id):
    row = _row(save_id, npc_id)
    return json.loads(row["known_npc_topics"]) if row else []


def all_relationships(save_id, today):
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM relationships WHERE save_id=?", (save_id,)).fetchall()
    return {
        r["npc_id"]: {
            "affection": _affection_from(
                r["starting_disposition"], json.loads(r["memories"]), today
            ),
            "last_talked_day": r["last_talked_day"],
            "last_message_day": r["last_message_day"],
            "last_date_week": r["last_date_week"],
            "known_npc_topics": json.loads(r["known_npc_topics"]),
            "known_player_topics": json.loads(r["known_player_topics"]),
        }
        for r in rows
    }
