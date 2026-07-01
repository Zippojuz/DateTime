"""Schema migrations: existing save files upgrade in place, no wipe needed."""

import sqlite3

import config
import db


def _use_db(tmp_path, monkeypatch, name):
    path = tmp_path / name
    monkeypatch.setattr(config, "DB_PATH", str(path))
    return str(path)


def test_existing_pre_migration_db_is_upgraded_in_place(tmp_path, monkeypatch):
    path = _use_db(tmp_path, monkeypatch, "old.db")

    # Simulate a pre-migration DB (user_version 0) whose tables predate the
    # preference/memory columns, with real data in them.
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE save (id INTEGER PRIMARY KEY AUTOINCREMENT);
        CREATE TABLE player (
            save_id INTEGER PRIMARY KEY,
            species TEXT NOT NULL DEFAULT 'human',
            attributes TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE relationships (
            save_id INTEGER NOT NULL,
            npc_id TEXT NOT NULL,
            last_talked_day INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (save_id, npc_id)
        );
        """
    )
    conn.execute("INSERT INTO save DEFAULT VALUES")
    conn.execute("INSERT INTO player (save_id, species) VALUES (1, 'human')")
    conn.execute("INSERT INTO relationships (save_id, npc_id) VALUES (1, 'vael')")
    conn.commit()
    conn.close()

    db.init_db()

    conn = db.get_connection()
    player_cols = [r["name"] for r in conn.execute("PRAGMA table_info(player)")]
    rel_cols = [r["name"] for r in conn.execute("PRAGMA table_info(relationships)")]
    assert "preferences" in player_cols
    for col in ("starting_disposition", "known_npc_topics", "known_player_topics", "memories"):
        assert col in rel_cols

    # Existing rows are preserved; new columns take their defaults.
    prow = conn.execute("SELECT species, preferences FROM player WHERE save_id=1").fetchone()
    assert prow["species"] == "human"
    assert prow["preferences"] == "{}"
    rrow = conn.execute(
        "SELECT memories FROM relationships WHERE save_id=1 AND npc_id='vael'"
    ).fetchone()
    assert rrow["memories"] == "[]"

    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    conn.close()


def test_fresh_db_gets_full_schema(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch, "fresh.db")
    db.init_db()

    conn = db.get_connection()
    player_cols = [r["name"] for r in conn.execute("PRAGMA table_info(player)")]
    assert "preferences" in player_cols
    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    conn.close()


def test_init_db_is_idempotent(tmp_path, monkeypatch):
    _use_db(tmp_path, monkeypatch, "again.db")
    db.init_db()
    db.init_db()  # second run must be a harmless no-op

    conn = db.get_connection()
    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    conn.close()
