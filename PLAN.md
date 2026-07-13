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
- **Tooling:** `ruff` (format + lint, Python), `eslint` + `prettier` (JS).
  Enforced via a `pre-commit` git hook (`.pre-commit-config.yaml`): ruff
  format/check + full pytest suite (backend), eslint + full vitest suite
  (frontend) — all run on every commit, whole codebase, not just staged files.
- **CI:** GitHub Actions (`.github/workflows/ci.yml`) mirrors the pre-commit
  gate on every push/PR (backend, frontend, and a `docker build` of the dev
  image) — the first place that verifies the Dockerfile actually builds, since
  this sandbox's egress policy blocks Docker Hub's layer CDN.
- **Tests:** `pytest` (backend) + `vitest` (frontend), one smoke test each in M0.
- **Attributes are data-driven + extensible.** Character stats/attributes are
  NOT fixed DB columns. They are defined in a registry (`data/attributes.json`)
  and stored as a keyed map on the character, so adding an attribute later is a
  one-line JSON entry — no schema migration. Charm/Wit/Courage/Empathy + Energy
  are just the first entries.
- **One shared Character model for player + NPCs.** Both use the *same* attribute
  set from the registry (NPCs mirror the player), with optional per-character
  overrides in `characters.json` (merge: registry defaults + overrides).
- **Player starts as `human`.** No species picker at creation for now; the alien
  species catalog and selection land in a later milestone.

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

## Milestone 0 — Scaffolding ✅ DONE

Goal: `flask run` serves a JSON API, `npm run dev` serves the React app, and the
two talk to each other with placeholder data.

**Status:** Complete. Backend boots and serves `/api/health`; frontend title
screen confirms the connection; `pytest` (3) and `vitest` (2) green; ESLint
clean; production build succeeds.

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

## Milestone 1 — Player Creation & Daily Loop (Design Phase 1) ✅ DONE

**Status:** Complete. Human player creation with the registry-backed shared
Character model, the daily action loop (rest/nap/explore/train/wait exercising
clock + energy), story-locked transformation, and single-save persistence.
Backend: 19 pytest. Frontend: 6 vitest, lint clean, build passes. Verified
end-to-end against a running server.


- [x] **`data/attributes.json`**: the extensible attribute registry. Each entry
      = id, display name, description, default, min/max (no grouping/category).
      Seeded with Charm/Wit/Courage/Empathy; designed so adding attributes later
      is a one-line addition (no schema change). Energy is a separate *player
      resource* (0–100 with regen), not a shared attribute.
- [ ] **`game/character.py`**: shared `Character` model backing BOTH player and
      NPCs. Holds `attributes` as a keyed map validated against the registry.
      NPCs mirror the player's attribute set; per-character overrides in
      `characters.json` merge over registry defaults.
- [ ] `player.py`: build on `Character` — Energy, identity fields
      (name/pronouns/appearance/body), and `species` defaulting to **`human`**
      (no species picker yet). Identity fields (gender, orientation, pronouns)
      are **free-form data, never gating flags** — no code path may branch on
      them to restrict content.
- [ ] **Locked initial state:** on creation the player commits name, pronouns,
      appearance, and body. Persist an immutable `created_identity` snapshot plus
      a mutable `current_identity` that starts equal to it.
- [ ] **Transformation unlock:** appearance / pronouns / genitals become editable
      only after story milestones grant the ability (a diegetic arc, not a
      day-one menu). Track unlocked transformation capabilities on the save.
      Endpoint: `POST /api/player/transform` (rejects changes to still-locked
      aspects). Pronoun changes propagate to how NPCs and text refer to you.
- [ ] DB: store attributes and identity as JSON blobs (not per-stat columns) so
      the schema stays stable as attributes grow.
- [ ] `POST /api/game/new` → create save + player; `GET /api/game/state`.
- [ ] `CreationScreen.jsx`: form for name, pronouns, appearance, body. (Species
      fixed to human for now — no picker.)
- [ ] `calendar.py`: clock that only advances on committed actions; day/time,
      week counter toward the 52-week year.
- [ ] `POST /api/action` — advance time, apply energy cost, return new state.
      Start with a minimal action set (Rest, Explore, Train, Wait) just to
      exercise time + energy; real activities layer in later milestones.
- [ ] `WorldMap` + `StatBar` showing time, energy, and attributes (rendered
      generically from the registry, so new attributes appear automatically).

**Done when:** create a character (human), take an action, watch the clock and
energy move, and see it persist across save/load.

---

## Milestone 2 — One Character, Full Vertical Slice (Design Phase 2) ✅ DONE

- [x] Implement **Vael** via `NPC` + `characters.json` (pronouns, schedule,
      availability windows). Dialogue text runs through a pronoun helper.
- [x] `social.py`: affection (0–100), scaled by arrival tier; one meaningful
      conversation per NPC per in-game day (gate, since dialogue is free).
- [x] `world.py`: schedule → availability with the "Arriving Late" tiers
      (full/shortened/brief/missed/unavailable), incl. midnight-crossing windows.
- [x] `dialogue.py`: branching tree from `data/dialogues.json` with light
      Charm/Wit stat gates + pronoun rendering.
- [x] `PeoplePanel`, `DialogueScreen`, `RelationshipPanel`.

**Decisions:** schedule-only reach (no travel yet — that's M3); branching +
stat-gated dialogue; conversations are free (no time/energy cost) with a
per-day gate to keep affection meaningful.

**Status:** Complete. Backend 37 pytest, frontend 9 vitest, lint clean, build
passes, verified end-to-end (unavailable → full tier → locked Charm choice →
affection gained → per-day gate → persists).

---

## Preferences, Compatibility & Memory ✅ DONE (added mid-M2)

- [x] `data/topics.json` — small, expandable opinion registry (books, sports,
      music, nightlife, fitness).
- [x] Preferences on the shared `Character` base: `topic → {sentiment,
      changeable}` (love/like/neutral/dislike/hate). Player seeded a default set;
      Vael's from `characters.json`; some marked `changeable: false` (core).
- [x] **Neutral affection** — recentered to a signed scale (−100…+100, 0 =
      neutral) with per-NPC `starting_disposition`; relationships seeded neutral.
- [x] **Hidden knowledge** — per-relationship discovery of NPC prefs (player
      side) and player prefs (NPC side); API redacts undiscovered NPC prefs.
- [x] **Asymmetric compatibility** — opposition penalized, shared-strong-feeling
      small bond, mere alignment neutral (`preferences.compatibility_delta`).
- [x] **Event-sourced memory** — affection derived from a memory log; offenses
      amplified when the bond is weak (up to 2×), decay by severity (minor 7d,
      moderate 30d, severe never); positives permanent.
- [x] Dialogue choices carry `reveal_npc` / `express` / `offense`; frontend shows
      the player's own opinions + discovered NPC opinions + a signed affection meter.

**Deferred:** the difficult *preference-change* mechanic (change your/their
likes; some unchangeable) — data models `changeable`, mechanic itself is next.

## Schema Migrations ✅ DONE

- [x] Versioned migration runner in `db.py` using `PRAGMA user_version`; only
      migrations newer than the DB's version run on boot. Existing save files
      upgrade in place (columns added, data preserved) — no wipe needed.
- [x] `_add_column` helper (add-if-missing) for safe `ALTER TABLE`s; append-only
      `MIGRATIONS` list.
- [x] Tests: real pre-migration DB upgrades in place, fresh DB gets full schema,
      `init_db` idempotent. Verified against a live legacy DB.

## Milestone 3 — Breadth (Design Phase 3) ✅ DONE

- [x] All 5 romanceable characters in `characters.json` (Zix, Sora, Carro, Miko
      added) with schedules (district-tagged), preferences, starting
      dispositions, and short intro dialogue trees.
- [x] All 5 districts (`districts.json`) as a ring with adjacency + vibes.
- [x] Travel system (`world.travel`): walk (free, slower) vs transit (credits,
      faster); adjacent vs cross-city costs; time + energy + credits applied.
      Player gains `location` + `credits` (migration 3).
- [x] **Co-location** — talking now requires being in the NPC's current district
      (supersedes M2's talk-from-anywhere); `/api/characters` reports `reachable`.
- [x] Random street encounters (`encounters.py` + `encounters.json`): flavor /
      merchant / trouble / sighting (tiny affection for someone you've met).
- [x] Frontend: TravelPanel, EncounterCard, district+credits HUD, PeoplePanel
      co-location ("in The Grid").

**Decisions:** credits system in now; talking requires physical co-location;
4 new characters get short stub intros; encounters are a basic data-driven pass.
**Status:** Backend 66 pytest, frontend green, lint clean, build passes.
Verified end-to-end (travel costs, co-location gate, reach Carro, encounter).

---

## Milestone 4 — Jobs, Debt & Seasonal Events (Design Phase 4) ✅ DONE

- [x] **Jobs** (`jobs.json`, `jobs.py`): district-based work; pay = base + a
      bonus from the job's stat; costs time + energy; co-location enforced.
- [x] **Debt** (`player.debt` + `debt_due_week`, migration 4): the debt that
      brought you here; `POST /api/debt/pay` to pay it down with credits — gives
      jobs/credits real purpose.
- [x] **Seasonal events** (`events.json`, `events.py`): date-gated calendar
      events that fire once when the clock reaches their (week, day) and surface
      as notifications; fired state on `player.fired_events`, threaded through
      the action/travel/job responses.
- [x] Routes: `/api/jobs`, `/api/job`, `/api/debt/pay`. Frontend: JobPanel,
      DebtPanel, EventLog.

**Status:** Backend 78 pytest, frontend green, lint clean, build passes.
Verified end-to-end (job pay + stat bonus, co-location gate, debt paydown,
arrival event firing). Events are notifications for now — deeper event scenes
(choices, dedicated dialogue) come with later story work.

## Milestone 6 — Inventory, Shop, Rarity & Gifting (Design Phase 6) ✅ MOSTLY DONE

- [x] **Inventory** (`inventory.py`, migration 5): `player.inventory` JSON blob;
      use food to restore energy (consumed).
- [x] **Items with rarity** (`items.json`): common/uncommon/rare/legendary across
      food + topic-tagged gifts.
- [x] **Shop** (`shop.py`, `shops.json`): per-district stock; price scales with
      rarity (`RARITY_PRICE_MULT`) × district modifier; browsing costs 30 min.
- [x] **Gifting** (`gifts.py`): reaction driven by the NPC's preference for the
      gift's topic (love +6 … hate −4), + a rarity effort bonus that softens but
      never flips a bad gift; routed through the memory system (offense on
      negatives); reveals the NPC's stance (discovery by action); one gift per
      NPC per day; co-location enforced.
- [x] **Relationship arcs (start)**: affection-threshold dialogue —
      `requires_affection` on trees; `tree_for_npc` picks the deepest qualifying
      one (Vael's tier-2 scene unlocks at 15). `/api/characters` exposes a stage
      label (stranger→acquaintance→friend→close/hostile).
- [x] Frontend: ShopPanel, InventoryPanel, GiftPicker, GiftReactionCard, rarity
      chips, Gift button + stage labels.

**Deferred:** crafting (recipes/materials — gifting doesn't need it); tier-2
scenes for the other four characters.
**Status:** Backend 93 pytest, frontend green, lint clean, build passes.
Verified end-to-end (rarity pricing, food use, preference-driven gift + reveal).

## Milestone 5 — Combat & The Substrate (Design Phase 5) ✅ DONE

- [x] **JRPG turn-based combat** (`combat.py`): attack / charge-cost elemental
      skills / guard / item / flee (never vs bosses); crits, variance; battle
      state persists on the player (survives reloads).
- [x] **Elements** (`elements.json`): two weakness triangles — thermal>cryo>
      voltaic>thermal, kinetic>toxin>psionic>kinetic (1.5x weak / 0.5x resist).
- [x] **The Substrate** (`dungeon.py`): procedurally generated floors from a
      per-run seed (deterministic resume), 9 floors; rooms = battles, events,
      treasure, rest; minibosses cap each floor, main bosses floors 3/6/9.
      Entrance in The Shallows.
- [x] **Enemies** (`enemies.json`): 12 regulars across 3 tiers + 3 minibosses +
      3 bosses — sci-fi, alluring, mostly female/androgynous (kept suggestive-
      tasteful per the design doc's later-gating stance).
- [x] **Dungeon events** (`dungeon_events.json`): terminals to hack (stat
      checks), healing pods, vending machines, glitch shrines, trapped crates,
      a flirtatious hologram.
- [x] **Tunable difficulty** (`difficulty.json`): easy/normal/hard multipliers
      on enemy hp/attack + xp rate; switchable any time.
- [x] **Persistent progression**: combat level + XP live on the player across
      runs/defeats ("remember your level"); max floor tracked. Defeat = ejected,
      lose 15% credits, never levels. Migration 6.
- [x] Routes: dungeon enter/state/advance/event/leave, combat action,
      difficulty get/set. Frontend: SubstratePanel (Shallows), DungeonScreen
      (floor map, events, treasure), BattleView (HP bars, skills, charge pips,
      log), level in StatBar.

**Status:** Backend 111 pytest, frontend green, lint clean, build passes.
Live scripted run: 6 floors, 19 wins, level 1→8, boss kills, events/treasure/
rest, defeat at the floor-6 boss with credits toll + level kept.

### Follow-up: loot & drops ✅ DONE
Per-role/tier drop tables (minibosses always drop, bosses roll twice), credit
variance (85–115%), dungeon-only items (Nano Patch, Charge Cell booster,
Singing Crystal, Voidglass Rose) never sold in shops; deep-floor treasure.

### Follow-up: equipment & gems (materia) ✅ DONE
- Ten JRPG gear slots: weapon, head, torso, arms, hands, legs, feet, ring1,
  ring2, accessory (ring items fit either finger — wear two).
- Gear gives flat stats + 0–2 gem sockets (rarer gear = more sockets); gems
  live on the equipped slot (inventory is quantity-based), unequip returns both.
- **Gems are materia**: element gem in the WEAPON changes your basic attack's
  element; the same gem in ARMOR resists that element (0.5x incoming). Stat,
  charge (start/max), XP% and credit% gems work anywhere.
- **Super rares** (boss jackpot roll, 12%): Prisma Gem (weapon: auto-targets
  the enemy's weakness; armor: resists everything) and the Empress's Heart.
- Gear/gems in shops (commons), loot tables, deep treasure; dungeon-only gear
  (Voidglass Edge, Neural Crown, Substrate Weave, Grav Dancers, Band of the
  Deep). Migration 7; routes /api/equipment + equip/unequip/socket/unsocket;
  EquipmentPanel UI with socket management. +16 pytest (152 total).

### Follow-up: boss mechanics & status effects ✅ DONE
- Telegraphed signature moves on a cadence (charge turn → ⚠ banner → big hit);
  guarding a telegraphed hit cuts it to 1/3 (regular guard 1/2).
- Phases at HP thresholds (data-driven `mechanics` in enemies.json): Contessa
  sheds armor (atk↑ def↓), Seraph shifts element voltaic→psionic mid-fight,
  Empress escalates twice. Minibosses each have one signature, no phases.
- Status effects: burn (DoT), slow (no charge regen), charm (your damage
  halved), corrode (defense halved). Bosses inflict via signatures; regular
  enemies via charged strikes (element-mapped); player thermal/toxin skills
  can inflict burn/corrode back. Status chips + telegraph banner in the UI.
- +15 pytest (136 total). Verified via full simulated boss fights (phase,
  telegraph, guard-read, status, double-drop all firing).

## Later Milestones (tracked, not detailed yet)

| Milestone | Design Phase | Notes |
|---|---|---|
| Story & seasonal events, jobs | 4 | ✅ DONE — see below |
| Combat | 5 | ✅ DONE — see below |
| Crafting, gifting, full arcs | 6 | ⚑ Gifting/inventory/shop DONE — see below; crafting deferred |
| Polish: real art, music, save/load UX, title | 7 | swap placeholders for assets |

---

## Open Questions to Resolve (from design doc)

- How mechanically significant is species? (perception abilities, interactions)
- Does combat integrate into the dating-sim loop, or sit beside it?
- Which "Weird Ideas" (city-as-organism, unreliable memory, the debt) are
  in-scope for v1 vs. stretch?

**Resolved:**
- Gender/orientation are fluid, non-mechanical, and never gate content —
  surfaced narratively only where relevant (see design doc → Identity
  Philosophy). Player identity is locked at creation, then
  appearance/pronouns/body become changeable through a story-gated
  transformation arc.
- Attributes are data-driven and extensible (registry + keyed map), shared
  between player and NPCs. Player starts as `human`; species selection and the
  alien catalog are deferred to a later milestone.

---

## Immediate Next Step

Execute **Milestone 1** — the attribute registry + shared `Character` model,
player creation (human), the daily action loop (clock + energy), and save/load
persistence. Milestone 0 (scaffolding) and the Docker dev container are done.
