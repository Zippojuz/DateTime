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

# --- Auto-login -------------------------------------------------------------
# Accounts exist now (flask-login, migration 19), but the game tests predate
# them and shouldn't each carry registration boilerplate. Every test client
# transparently registers/logs in a shared "tester" account before its first
# /api request. Auth tests opt out with `client.no_auto_login = True` to
# exercise the real flow.

from flask.testing import FlaskClient  # noqa: E402

_orig_open = FlaskClient.open


def _auto_login_open(self, *args, **kwargs):
    if not getattr(self, "_auto_logged_in", False) and not getattr(self, "no_auto_login", False):
        self._auto_logged_in = True  # set first — the calls below recurse into open()
        path = str(args[0]) if args else str(kwargs.get("path", ""))
        if path.startswith("/api") and not path.startswith("/api/auth"):
            creds = {"username": "tester", "password": "hunter22"}
            res = _orig_open(self, "/api/auth/register", method="POST", json=creds)
            if res.status_code == 400:  # already exists (shared test DB)
                _orig_open(self, "/api/auth/login", method="POST", json=creds)
    return _orig_open(self, *args, **kwargs)


FlaskClient.open = _auto_login_open
