# NEXUS CITY

A sci-fi dating sim / JRPG. Flask (Python) backend + React (Vite) frontend,
SQLite saves. See [`dtDesignDoc.md`](dtDesignDoc.md) for the design and
[`PLAN.md`](PLAN.md) for the build plan and architecture decisions.

## Status

Milestones 0–4 and most of 6 are built: player creation, the daily action loop,
NPC relationships/dialogue/preferences with memory decay, an explorable
5-district city, jobs/debt/seasonal events, and inventory/shop/gifting. See
`PLAN.md` for the full milestone breakdown and what's next.

## Layout

```
backend/    Flask API, game logic (stubs), SQLite, JSON data
frontend/   React + Vite, Zustand store
```

## Run with Docker (one command)

The whole app runs in a single dev container (Flask + Vite, hot reload) — no
local Python or Node needed, just Docker.

```bash
bash scripts/docker-dev.sh
```

Then open http://localhost:5173 — the title screen should read **"Connected to
Nexus core"**. Editing files under `backend/` or `frontend/` hot-reloads live
(source is bind-mounted). Ctrl-C stops the container.

> This is a development image, not a production build. See `PLAN.md` for the
> (out-of-scope-for-now) production path.

## Run locally (two terminals)

Prefer running on the host directly? You'll need:

- Python 3.11+
- Node 20+ / npm

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                    # serves http://localhost:5000
```

Health check: `curl http://localhost:5000/api/health` → `{"status": "ok", ...}`

### Frontend

```bash
cd frontend
npm install
npm run dev                      # serves http://localhost:5173
```

Open http://localhost:5173 — the title screen should read **"Connected to
Nexus core"** once it reaches the backend. (Vite proxies `/api` to the backend,
so both must be running.)

## Tests

```bash
# Backend
pip install -r backend/requirements-dev.txt
pytest

# Frontend
cd frontend && npm test
```

## Pre-commit hooks

`bash scripts/dev-setup.sh` installs dev tooling and registers a git
pre-commit hook (config in `.pre-commit-config.yaml`). Every commit runs, on
the **whole codebase** (not just staged files):

- `ruff format` + `ruff check` (backend)
- the full `pytest` suite (backend)
- `eslint` + the full `vitest` suite (frontend)

A commit is blocked until all five pass. To run it manually:
`backend/.venv/bin/pre-commit run --all-files`. To set it up by hand instead of
via `dev-setup.sh`: `pip install -r backend/requirements-dev.txt && pre-commit
install`.

## Conventions

- Backend is **server-authoritative** — game rules and state live in Python.
- Identity fields (pronouns/gender/orientation/appearance/body) are free-form
  data and never gate content. See `dtDesignDoc.md` → Identity Philosophy.
- Python: `ruff` (format + lint). JS: `eslint` + `prettier`.
- Enforced on every commit — see Pre-commit hooks above.
