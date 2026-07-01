"""Test setup: point the DB at a throwaway temp file before app import."""

import os
import tempfile

os.environ.setdefault(
    "NEXUS_DB_PATH", os.path.join(tempfile.gettempdir(), "nexus_test.db")
)
