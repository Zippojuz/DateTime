"""SQLite access + schema migrations.

Schema changes are applied through an ordered list of migrations, versioned via
SQLite's ``PRAGMA user_version``. On every boot we run only the migrations newer
than the DB's recorded version, so an existing save file is upgraded in place
(new columns added, data preserved) rather than needing a wipe.

To evolve the schema: append a new migration function to ``MIGRATIONS`` — never
edit or reorder an existing one (that would desync already-migrated DBs).

Attributes, identity, preferences, and the affection memory log are stored as
JSON blobs (not per-field columns) so most content changes need no migration at
all — see PLAN.md.
"""

import sqlite3

import config

# --- Table definitions (current/final shape) --------------------------------

_SAVE = """
CREATE TABLE IF NOT EXISTS save (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
    schema_version INTEGER NOT NULL DEFAULT 1
);
"""

_PLAYER = """
CREATE TABLE IF NOT EXISTS player (
    save_id                  INTEGER PRIMARY KEY REFERENCES save(id) ON DELETE CASCADE,
    species                  TEXT    NOT NULL DEFAULT 'human',
    attributes               TEXT    NOT NULL,               -- JSON map
    preferences              TEXT    NOT NULL DEFAULT '{}',  -- JSON map
    energy                   INTEGER NOT NULL DEFAULT 100,
    created_identity         TEXT    NOT NULL,               -- JSON, immutable snapshot
    current_identity         TEXT    NOT NULL,               -- JSON
    unlocked_transformations TEXT    NOT NULL DEFAULT '[]',  -- JSON list
    location                 TEXT    NOT NULL DEFAULT 'docking_quarter',
    credits                  INTEGER NOT NULL DEFAULT 50,
    debt                     INTEGER NOT NULL DEFAULT 500,
    debt_due_week            INTEGER NOT NULL DEFAULT 52,
    fired_events             TEXT    NOT NULL DEFAULT '[]',  -- JSON list of event ids
    inventory                TEXT    NOT NULL DEFAULT '{}',  -- JSON map item_id -> qty
    clock_week               INTEGER NOT NULL DEFAULT 1,
    clock_day                INTEGER NOT NULL DEFAULT 1,
    clock_minute             INTEGER NOT NULL DEFAULT 480
);
"""

_RELATIONSHIPS = """
CREATE TABLE IF NOT EXISTS relationships (
    save_id              INTEGER NOT NULL REFERENCES save(id) ON DELETE CASCADE,
    npc_id               TEXT    NOT NULL,
    starting_disposition INTEGER NOT NULL DEFAULT 0,   -- signed baseline; 0 = neutral
    last_talked_day      INTEGER NOT NULL DEFAULT 0,   -- absolute day index; 0 = never
    known_npc_topics     TEXT    NOT NULL DEFAULT '[]', -- topics the player learned about the NPC
    known_player_topics  TEXT    NOT NULL DEFAULT '[]', -- topics the NPC learned about the player
    memories             TEXT    NOT NULL DEFAULT '[]', -- affection event log (derives affection)
    last_gift_day        INTEGER NOT NULL DEFAULT 0,   -- one gift per NPC per day
    PRIMARY KEY (save_id, npc_id)
);
"""


# --- Migration helpers ------------------------------------------------------


def _column_exists(conn, table, column):
    return any(row["name"] == column for row in conn.execute(f"PRAGMA table_info({table})"))


def _add_column(conn, table, column, decl):
    """ALTER TABLE ADD COLUMN, but only if the column is missing (so it's safe on
    DBs that already have it)."""
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


# --- Migrations (append-only; order matters) --------------------------------


def _m1_base_schema(conn):
    """The three core tables in their current shape (Milestones 0–2)."""
    conn.executescript(_SAVE + _PLAYER + _RELATIONSHIPS)


def _m2_preferences_and_memory(conn):
    """Add preference + memory columns to DBs created before they existed.

    No-op on fresh DBs (the base-schema tables already include these). Upgrades
    older save files in place, defaulting the new columns for existing rows.
    """
    _add_column(conn, "player", "preferences", "TEXT NOT NULL DEFAULT '{}'")
    _add_column(conn, "relationships", "starting_disposition", "INTEGER NOT NULL DEFAULT 0")
    _add_column(conn, "relationships", "known_npc_topics", "TEXT NOT NULL DEFAULT '[]'")
    _add_column(conn, "relationships", "known_player_topics", "TEXT NOT NULL DEFAULT '[]'")
    _add_column(conn, "relationships", "memories", "TEXT NOT NULL DEFAULT '[]'")


def _m3_location_and_credits(conn):
    """Add player location + credits (Milestone 3: travel)."""
    _add_column(conn, "player", "location", "TEXT NOT NULL DEFAULT 'docking_quarter'")
    _add_column(conn, "player", "credits", "INTEGER NOT NULL DEFAULT 50")


def _m4_jobs_debt_events(conn):
    """Add debt tracking + fired-event log (Milestone 4: jobs & events)."""
    _add_column(conn, "player", "debt", "INTEGER NOT NULL DEFAULT 500")
    _add_column(conn, "player", "debt_due_week", "INTEGER NOT NULL DEFAULT 52")
    _add_column(conn, "player", "fired_events", "TEXT NOT NULL DEFAULT '[]'")


def _m5_inventory_and_gifts(conn):
    """Add player inventory + per-day gift gate (Milestone 6)."""
    _add_column(conn, "player", "inventory", "TEXT NOT NULL DEFAULT '{}'")
    _add_column(conn, "relationships", "last_gift_day", "INTEGER NOT NULL DEFAULT 0")


MIGRATIONS = [
    _m1_base_schema,
    _m2_preferences_and_memory,
    _m3_location_and_credits,
    _m4_jobs_debt_events,
    _m5_inventory_and_gifts,
]


# --- Connection + init ------------------------------------------------------


def get_connection():
    """Open a SQLite connection with row access by column name."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Bring the DB up to the latest schema version. Safe to call on every boot;
    runs only the migrations newer than the DB's recorded ``user_version``."""
    with get_connection() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        for migration in MIGRATIONS[version:]:
            migration(conn)
        # user_version can't be parameterised; len(MIGRATIONS) is a trusted int.
        conn.execute(f"PRAGMA user_version = {len(MIGRATIONS)}")
