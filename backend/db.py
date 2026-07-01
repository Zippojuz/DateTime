"""SQLite access + schema initialisation.

Milestone 0 keeps the schema intentionally minimal — just enough to prove the
save layer wires up. It expands in Milestone 1 (player, identity) and beyond.
"""

import sqlite3

import config

# Attributes and identity are stored as JSON blobs (not per-stat columns) so the
# schema stays stable as attributes grow — see PLAN.md.
SCHEMA = """
CREATE TABLE IF NOT EXISTS save (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    schema_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS player (
    save_id                  INTEGER PRIMARY KEY REFERENCES save(id) ON DELETE CASCADE,
    species                  TEXT    NOT NULL DEFAULT 'human',
    attributes               TEXT    NOT NULL,          -- JSON map
    energy                   INTEGER NOT NULL DEFAULT 100,
    created_identity         TEXT    NOT NULL,          -- JSON, immutable snapshot
    current_identity         TEXT    NOT NULL,          -- JSON
    unlocked_transformations TEXT    NOT NULL DEFAULT '[]',  -- JSON list
    clock_week               INTEGER NOT NULL DEFAULT 1,
    clock_day                INTEGER NOT NULL DEFAULT 1,
    clock_minute             INTEGER NOT NULL DEFAULT 480
);
"""


def get_connection():
    """Open a SQLite connection with row access by column name."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create tables if they don't already exist. Safe to call on every boot."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
