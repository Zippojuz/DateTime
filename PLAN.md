# NEXUS CITY — Implementation Plan

A working plan that turns `dtDesignDoc.md` into buildable steps. Focus for the
first milestones is **scaffolding** — get the skeleton of the Flask + React app
in place so systems can be layered in per the design doc's Build Phases.

---

## Architecture Decisions (locked)

- **Stack:** Flask (Python) backend + React (Vite) frontend + SQLite saves.
- **Logic authority:** **Flask is server-authoritative.** Python owns all game
  state, rules, and the identity-gating guarantees; React is a thin view that
  calls the API. One source of truth.
- **Repo layout:** `backend/` and `frontend/` live at the **repo root** (this
  repo *is* the game — no `my_jrpg/` wrapper).
- **Frontend state:** **Zustand** — one authoritative game-state store synced
  from the API.
- **API:** REST, JSON, all routes under `/api`, consistent `{error, ...}` shape.
- **Saves:** single autosave slot for now; multi-slot deferred to Phase 7.
- **Python deps:** `venv` + `requirements.txt`.
- **Tooling:** `ruff` + `black` (Python), `eslint` + `prettier` (JS).
- **Tests:** `pytest` (backend) + `vitest` (frontend), one smoke test each in M0.

## Guiding Principles

- **Scaffold first, features second.** Stand up the folder structure, a running
  backend, a running frontend, and the API contract between them before writing
  any real gameplay logic.
- **Placeholder art only** (per the design doc's Art Strategy) — colored boxes
  and CSS until systems feel good.
- **Data-driven.** Characters, items, events, and dialogue live in JSON under
  `backend/data/` so writing/design doesn't require code changes.
- **Vertical slice.** After scaffolding, prove one full loop end-to-end (create
  player → advance time → one interaction) before going wide.

---

## Target Structure

```
my_jrpg/
├── backend/                  # Python / Flask
│   ├── app.py                # Flask entry point, route registration
│   ├── requirements.txt
│   ├── config.py             # env, DB path, constants
│   ├── db.py                 # SQLite connection + schema init
│   ├── game/
│   │   ├── __init__.py
│   │   ├── player.py         # stats, energy, creation
│   │   ├── world.py          # districts, travel, hours
│   │   ├── calendar.py       # clock, days, 52-week year
│   │   ├── social.py         # affection, relationships
│   │   ├── dialogue.py       # dialogue tree runner
│   │   ├── battle.py         # (Phase 5 — stub for now)
│   │   └── crafting.py       # (Phase 6 — stub for now)
│   └── data/
│       ├── characters.json
│       ├── enemies.json
│       ├── items.json
│       └── events.json
│
└── frontend/                 # React
    └── src/
        ├── api/              # fetch wrappers for backend
        ├── state/            # game state store
        ├── screens/
        │   ├── TitleScreen.jsx
        │   ├── CreationScreen.jsx
        │   ├── WorldMap.jsx
        │   ├── DialogueScreen.jsx
        │   ├── CalendarScreen.jsx
        │   ├── BattleScreen.jsx
        │   └── MenuScreen.jsx
        └── components/
            ├── StatBar.jsx
            ├── SkillTree.jsx
            ├── Inventory.jsx
            └── RelationshipPanel.jsx
```

---

## Milestone 0 — Scaffolding (do this first)

Goal: `flask run` serves a JSON API, `npm run dev` serves the React app, and the
two talk to each other with placeholder data.

### Backend
- [ ] Create `backend/` with `app.py`, `config.py`, `db.py`, `requirements.txt`
      (`flask`, `flask-cors`).
- [ ] `db.py`: open SQLite, create tables on first run (`save`, `player`,
      `relationships`). Keep schema minimal — expand later.
- [ ] Stub `game/` modules with empty classes/functions and docstrings so the
      import graph is real.
- [ ] Seed `data/*.json` with 1–2 example entries each (one district, one
      character = Vael with a `pronouns` field, one item).
- [ ] Health route `GET /api/health` → `{"status": "ok"}`.

### Frontend
- [ ] Scaffold React app (Vite recommended) under `frontend/`.
- [ ] `src/api/client.js` — base fetch wrapper pointing at the Flask dev server.
- [ ] Render `TitleScreen` that calls `/api/health` and shows the result.
- [ ] Dark/neon placeholder CSS theme (per design doc's UI direction).

### Glue
- [ ] Enable CORS on the backend for the dev frontend origin.
- [ ] Document run commands in a top-level `README.md`.

**Done when:** both servers run, and the title screen confirms it reached the API.

---

## Milestone 1 — Player Creation & Daily Loop (Design Phase 1)

- [ ] `player.py`: stats (Charm/Wit/Courage/Empathy), Energy (0–100),
      name/pronouns/species/appearance/body. Identity fields (gender,
      orientation, pronouns) are **free-form data, never gating flags** — no code
      path may branch on them to restrict content.
- [ ] **Locked initial state:** on creation the player commits name, pronouns,
      appearance, and body. Persist an immutable `created_identity` snapshot plus
      a mutable `current_identity` that starts equal to it.
- [ ] **Transformation unlock:** appearance / pronouns / genitals become editable
      only after story milestones grant the ability (a diegetic arc, not a
      day-one menu). Track unlocked transformation capabilities on the save.
      Endpoint: `POST /api/player/transform` (rejects changes to still-locked
      aspects). Pronoun changes propagate to how NPCs and text refer to you.
- [ ] `POST /api/game/new` → create save + player; `GET /api/game/state`.
- [ ] `CreationScreen.jsx`: form for name, pronouns, species, appearance, body.
- [ ] `calendar.py`: clock that only advances on committed actions; day/time,
      week counter toward the 52-week year.
- [ ] `POST /api/action` — advance time, apply energy cost, return new state.
- [ ] `WorldMap` + `StatBar` showing time, energy, stats.

**Done when:** create a character, take an action, watch the clock and energy move.

---

## Milestone 2 — One Character, Full Vertical Slice (Design Phase 2)

- [ ] Implement **Vael** fully from `characters.json` (pronouns, schedule,
      availability windows, arc theme). Dialogue text uses a pronoun helper so
      NPC and narration text renders correct pronouns for both the character and
      the (possibly changed) player.
- [ ] `social.py`: affection track + gain/loss rules.
- [ ] `world.py`: district hours + character schedules → is-available check,
      including the "Arriving Late" tiers.
- [ ] `dialogue.py`: run a branching dialogue tree from JSON.
- [ ] `DialogueScreen` + `RelationshipPanel`.

**Done when:** travel to Vael during an availability window, hold a dialogue,
gain affection, see it persist across save/load.

---

## Milestone 3 — Breadth (Design Phase 3)

- [ ] Stub all 5 romanceable characters in `characters.json`.
- [ ] All 5 districts explorable with hours and travel time/costs.
- [ ] Travel system with time cost + placeholder random-encounter hook.

---

## Later Milestones (tracked, not detailed yet)

| Milestone | Design Phase | Notes |
|---|---|---|
| Story & seasonal events, jobs | 4 | `events.json` + calendar triggers |
| Combat | 5 | `battle.py` — integration approach still TBD in design doc |
| Crafting, gifting, full arcs | 6 | `crafting.py`, `items.json` |
| Polish: real art, music, save/load UX, title | 7 | swap placeholders for assets |

---

## Open Questions to Resolve (from design doc)

- How mechanically significant is species? (perception abilities, interactions)
- Does combat integrate into the dating-sim loop, or sit beside it?
- Which "Weird Ideas" (city-as-organism, unreliable memory, the debt) are
  in-scope for v1 vs. stretch?

**Resolved:** Gender/orientation are fluid, non-mechanical, and never gate
content — surfaced narratively only where relevant (see design doc → Identity
Philosophy). Player identity is locked at creation, then appearance/pronouns/body
become changeable through a story-gated transformation arc.

---

## Immediate Next Step

Execute **Milestone 0** — scaffold `backend/` and `frontend/` with running
servers and a health-check handshake. Everything else builds on that skeleton.
