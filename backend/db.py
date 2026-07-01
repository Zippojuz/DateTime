"""SQLite access + schema initialisation.

Milestone 0 keeps the schema intentionally minimal — just enough to prove the
save layer wires up. It expands in Milestone 1 (player, identity) and beyond.
"""

import sqlite3

import config

# Minimal starter schema. Columns are added as milestones land; for now this
# only proves the DB initialises and is reachable.
SCHEMA = """
CREATE TABLE IF NOT EXISTS save (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    schema_version INTEGER NOT NULL DEFAULT 1
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
