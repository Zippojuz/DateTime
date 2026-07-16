"""Runtime configuration for the Nexus City backend.

Values are read from the environment so the same code runs in dev, test, and
(eventually) production without edits.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Where the SQLite save database lives. Overridden in tests to a temp file.
DB_PATH = os.environ.get("NEXUS_DB_PATH", str(BASE_DIR / "nexus.db"))

# The React dev server origin, allowed through CORS during development.
FRONTEND_ORIGIN = os.environ.get("NEXUS_FRONTEND_ORIGIN", "http://localhost:5173")

# Signs the session cookie (flask-login). The default is fine for local dev;
# ANY real deployment must set NEXUS_SECRET_KEY to something private.
SECRET_KEY = os.environ.get("NEXUS_SECRET_KEY", "dev-only-not-a-secret")

# Backend dev server bind address + port. Defaults to loopback for local runs;
# the Docker container sets NEXUS_HOST=0.0.0.0 so it's reachable from the host.
HOST = os.environ.get("NEXUS_HOST", "127.0.0.1")
PORT = int(os.environ.get("NEXUS_PORT", "5000"))
