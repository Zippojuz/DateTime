# NEXUS CITY

A sci-fi dating sim / JRPG. Flask (Python) backend + React (Vite) frontend,
SQLite saves. See [`dtDesignDoc.md`](dtDesignDoc.md) for the design and
[`PLAN.md`](PLAN.md) for the build plan and architecture decisions.

## Status

**Milestone 0 — Scaffolding.** Both servers run and the title screen confirms
it reached the backend's health endpoint. Game systems are stubbed.

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
pip install -r backend/requirements.txt
pytest

# Frontend
cd frontend && npm test
```

## Conventions

- Backend is **server-authoritative** — game rules and state live in Python.
- Identity fields (pronouns/gender/orientation/appearance/body) are free-form
  data and never gate content. See `dtDesignDoc.md` → Identity Philosophy.
- Python: `ruff` + `black`. JS: `eslint` + `prettier`.
