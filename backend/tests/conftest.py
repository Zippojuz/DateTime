"""Test setup: point the DB at a fresh throwaway temp file before app import.

The file is removed at collection time for deterministic test isolation (no
stale data between runs). Schema upgrades themselves are handled by migrations
(see db.py) and covered by test_migrations.py.
"""

import os
import tempfile

_db = os.path.join(tempfile.gettempdir(), "nexus_test.db")
os.environ["NEXUS_DB_PATH"] = _db
if os.path.exists(_db):
    os.remove(_db)
