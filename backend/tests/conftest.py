"""Test setup: point the DB at a fresh throwaway temp file before app import.

The file is removed at collection time so each run starts on the current schema
(CREATE TABLE IF NOT EXISTS does not migrate columns onto an existing DB).
"""

import os
import tempfile

_db = os.path.join(tempfile.gettempdir(), "nexus_test.db")
os.environ["NEXUS_DB_PATH"] = _db
if os.path.exists(_db):
    os.remove(_db)
