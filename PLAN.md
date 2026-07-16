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

### Follow-up: Zork-style dungeon (maps, hidden rooms, puzzles) ✅ DONE
- Floors are seeded room GRAPHS on a lattice (10–13 rooms + hidden), compass
  exits with flavor labels, loops not just branches; moving = one action (5m).
- **Fog of war**: the server only ever sends visited rooms + doorway stubs;
  the map UI draws itself as you explore.
- **Room descriptions** from themed fragment pools by depth (maintenance decks
  → grown corridors → dream-architecture) — `dungeon_rooms.json`.
- **Hidden rooms**: 1–2 per floor behind concealed exits; room text hints,
  explicit Search action (Wit + d6 vs DC 7) reveals; premium caches inside.
- **Puzzles** (non-boss floors, stairs locked): keycard hidden in a far room,
  or power routing (two generators to unseal the bulkhead). Boss floors
  (3/6/9): the boss camps in the stairwell. Puzzle floors also carry an
  optional miniboss hoard (premium loot).
- **Telegraphed threats**: uncleared enemies leak hints through doorways
  ("something is ticking beyond the east door"); cleared rooms stay clear;
  fleeing returns you the way you came.
- Routes: /api/dungeon/move|search|interact replace /advance. New DungeonScreen:
  fog-of-war grid map, room prose, compass exit buttons, Search/Interact.
- +14 pytest (166 total). Verified with a live delve: generators, keycards,
  searches → caches, minibosses, the floor-3 boss, defeat ejection.

### Follow-up: curios & companions ✅ DONE
- **Curios** (`curios.json`): strange interactable objects, 2–3 scattered per
  floor — chrome mannequins, mirror pools, glitter moths, whispering vents.
  Examine is free and repeatable; other verbs (touch/kiss/rest/take/offer/
  listen/wake) cost 5m, are one-shot per placement, and pay out through the
  shared outcome engine (heal, buff, credits, items, XP, XP-for-blood,
  full-map reveal). Kept sci-fi/sexy/weird per direction. Route
  POST /api/dungeon/curio; verb buttons in DungeonScreen.
- **Companions**: one delving partner at a time (roles make the choice
  matter). All five romanceables have a `companion` block: Vael tank/cryo,
  Zix dps/voltaic, Sora healer/toxin, Carro rogue/kinetic (+25% credits),
  Miko support/psionic (+1 charge/turn). Recruit gate: affection ≥ 25
  (friend); recruit/dismiss only topside (POST /api/party/recruit|dismiss,
  GET /api/party).
- In combat the companion auto-acts each round by role (healer heals+cleanses
  below 60%, dps 1.3x, support feeds charge, tank draws 55% of enemy fire and
  shoulders 30% of player hits). At 0 HP they go DOWN (not dead) until a rest
  stop. Elemental multipliers apply to their strikes.
- **The bond loop**: leaving a run together grants affection (2 + floor//2,
  cap 6); even a defeat grants +1 — the dungeon feeds the dating sim.
- Migration 8 (`player.companion`); companion state persisted inside the run
  blob. UI: party picker in SubstratePanel, companion HP in the dungeon
  header, companion card in BattleView. +26 pytest (192 total). Verified with
  a live run: recruit gate, mid-run lock, curio verbs + once-only, combat
  assists, leave bond (+2 on floor 1), dismiss.

### Follow-up: black-market cred tiers ✅ DONE
- The Static Bazaar grows three back rooms gated by street cred, aligned
  with the cred stages: **The Back Shelf** (10 — Gutterware Coolant Sleeve,
  Burner Blade, Duelist Gauntlets, Lucky Chip), **The Locked Case** (40 —
  Flechette Pistol, Ghostweave Vest, Psi Gem), **The Basement** (100 —
  Warlord Frame, Midnight Gem: legendary contraband).
- Shops support ``cred_tiers`` generically (shop.tiers/_purchasable_ids):
  locked tiers return only a tease + item count — the goods never leave the
  server; buying below the threshold gets "The dealer's eyes slide past you
  like you're furniture." ShopPanel renders open rooms with gold headers and
  locked ones as 🔒 teaser rows showing required vs current cred; the shop
  refreshes when cred moves (arena outcomes, dungeon depth records).
- Data-integrity tests (dungeon-only, duplicates) now sweep tier stock too.
  +7 pytest (284 total); verified live at 0 and 45 cred in-browser.
- **Dirty gigs pay cred**: every dirty fork on Vex's board grants +3 street
  cred ("the wrong people notice, approvingly") on top of the better pay and
  the cast offense — clean work builds no such name. Shown on the gig
  buttons/results; the shop refreshes after gigs since cred can open Bazaar
  rooms. (+2 pytest, 285 total.)

### Follow-up: The Pit (battle arena) + street cred ✅ DONE
- **The Pit** (`arena.json` + `game/arena.py`): unlicensed ring in a drained
  ballast tank under the Docking Quarter. Pure win ladder — losses cost
  nothing and don't advance it; bouts pay NO XP, NO credits, NO drops
  (combat's arena flag) — one cred per win. No companions ("no seconds").
  Full HP each bout; 10 energy, 45 min.
- **Every 10th WIN is a championship** against a named champion: Mirrorblade
  Duessa (10, kinetic), Saint Voltage (20, voltaic), The Gravekeeper Lull
  (30, cryo), and Zenith the Crowd's Own (40, psionic, three phases with
  element shifts). Lull and Zenith out-stat floor-10 Nyx — the hardest fights
  in the game. Titles pay a purse (100/200/400/800), a unique prize
  (Champion's Belt / Voltage Halo / Gravekeeper's Signet / Zenith's Sigil)
  and big cred (15/25/40/60). Past 40: Apex rematches (cred + purse only).
  Regular bouts draw from tier pools scaled by bracket; championships can't
  be fled.
- **Street cred** (migration 11: street_cred + arena_wins): championships,
  every Pit win, and NEW dungeon depth records (2 x floor, once per floor).
  Stages: Unknown → Known Face → Name in the Grid → Undercard Legend →
  Crowd's Own. Shown on the stat bar; reserved as a gate for future
  black-market tiers/dialogue.
- Routes GET /api/arena + POST /api/arena/fight; combat finish branches to
  arena vs dungeon. ArenaPanel (gold championship card), BattleView now rides
  over the world map for run-less fights, CombatOutcome gets CHAMPION
  fanfare (title/purse/prize/cred) and Pit-flavored defeat/forfeit copy.
  +15 pytest (279 total); verified live — 9-win climb (zero XP/credit gain),
  Gatekeeper's Bout and The Canonization both won in-browser.

### Follow-up: the Pit becomes a real place + Ondo the pit master ✅ DONE
- **Places layer** (`game/places.py` + `data/venues.json`): a *place* is a
  district OR a venue nested inside one; `player.location` may hold either.
  Neighborhood rules (travel cost/adjacency) resolve via `district_of()`;
  room rules (NPC reach, shops, fight gates) compare place ids exactly.
  Venues keep hours (midnight-wrapping); districts never close. Travel gains
  a **local hop** (5 min / 1 energy) for same-district moves; entering a
  closed venue is refused with its `closed_line`. New venues = one JSON
  entry (gym, library etc. later). GET /api/venues; travel accepts venue ids.
- **The Pit moved into The Grid** — a drained coolant cistern three levels
  under the district (cred stage "Name in the Grid" now literal). Open
  16:00–04:00; fights require being *inside* during open hours. TravelPanel
  shows gold venue chips ("here · 16:00–04:00 · Enter · 5m"), the HUD reads
  "The Pit · under The Grid", PitView (replaces ArenaPanel) renders the whole
  venue: fight card, closed-state, the belt rack, and the book.
- **Ondo "The Bell" Marr** (they/them, andro-masc): ninth cast member, the
  Pit's founder — retired undefeated 15 years ago, mid-fight, and won't say
  why. Ringside 16:00–04:00 (reachable only inside the venue), romanceable,
  loves sports/fitness, hates betting on fighters ("you've decided what
  they're worth before they show you"). `ondo_intro` dialogue with
  record-aware bell-line greetings on the arena board.
- **The Founder's Bout (fight #50)**: Ondo steps into their own ring once —
  the true apex, out-statting Zenith on every stat (420hp/34atk/17def/22spd,
  First Bell telegraph, FINAL ROUND enrage). NO purse ("you don't get paid to
  beat them; you get remembered") — 100 cred + the legendary Founder's Bell.
  Championship wins now leave `defeated:<enemy>` markers (same as dungeon
  bosses); Ondo's tank companion (hp×1.5) and the answer to their retirement
  (a `requires_event`-hidden dialogue choice — new dialogue capability,
  hidden not locked, so payoffs don't spoil themselves) both key off beating
  them. #60+ falls through to Apex rematches unchanged.
- **The book + belt rack**: arena.json leaderboard of nine named fighters
  (Zenith 214W … Moth 8W) with the player's row spliced in by wins (ties go
  to the named fighter); Ondo sits above the table, unranked, "Undefeated
  (retired)". Belts show holder → YOURS as titles are taken. Victory
  outcomes carry a crowd line keyed to your cred stage.
- +20 pytest (305 total, incl. dialogue event-gating and venue travel), 18
  vitest; verified live end-to-end (closed-door refusal at 08:00, evening
  entry, Ondo talk/gift, bout win, locked recruit refusal) + Playwright
  screenshots of PitView/travel chips/HUD.

### Follow-up: species registry + the Hold (gym) + Oona ✅ DONE
- **species.json**: a registry of ten suggestions (Human, Self-Owned Chassis,
  Uplift, Warform, Hivemind Colony, Feathered Avian, Reptilian Cold-blood,
  Plant-Fungal Hybrid, Bioluminescent, Substrate-Born) — **suggestions, never
  gates**. Creation screen grows a species picker: registry chips with lore
  blurbs + a free-text field that accepts anything verbatim (GET /api/species;
  /api/game/new takes species; Player.create passes it through; default stays
  "human"). Species remains immutable post-creation per the identity doc.
- **The Hold**: second venue (Docking Quarter) — a gutted cargo hold refitted
  as a gym, 06:00–23:00, with a brine tank aft. Venues gain a generic
  ``training`` block: **house rates** discount coached attributes (Agility &
  Courage: 1h / −8 energy vs the street's 2h / −15) via
  actions.house_rates(); other attributes pay full price ("charm you'll have
  to find in a bar"). The action panel shows the gold house-rates note inside
  a coaching venue.
- **Oona** (she/her, "Uplifted octopus (exo-rig)"): tenth cast member, head
  coach — lab-uplifted by Oceania for aquaculture inventory, forged her own
  release paperwork with four arms at once. Ringside... floorside 06:00–13:00
  and 15:00–23:00; in the tank (unavailable, do not knock) 13:00–15:00 and
  overnight. Loves fitness, likes sports/books, hates nightlife. Support
  companion (cryo, atk×1.1) behind the normal affection gate. `oona_intro`
  full of anatomy sarcasm, the tank-is-bought-not-issued beat, and a
  calamari-joke offense branch.
- +11 pytest (316 total) incl. species free-text, house-rate boundaries, tank
  hours, API creation flow; CreationScreen vitest rewritten for chips+custom.
  Verified live: Uplift character created, Hold entered at 08:05, agility
  trained at −8/1h vs wit at −15/2h, Oona talked, tank hours refused, and
  the Hold→Pit hop correctly refused at 13:00 (Pit closed).

### Follow-up: species traits ✅ DONE
- **Design doc AMENDED** (user decision): species MAY be mechanical — traits,
  flavored dialogue, minor gates — under two hard rules: the main romance
  pathway is never species-gated (every dialogue node keeps a trait-free
  path, enforced by an integrity test), and gender/orientation stay
  never-mechanical. The "should species have mechanical implications?" open
  question is RESOLVED.
- **Traits** (species.json ``trait`` blocks + game/traits.py): one shared
  knack per registry species, like a class built from what a body is.
  Human **Priced In** (free transit, 10% shop discount) · Chassis
  **Maintenance Cycle** (4h full rest) · Uplift **Escape Artist** (flee
  always works, +0.03 dodge; bosses still corner you) · Warform **Built For
  It** (+10% max HP, guard cuts telegraphs to 1/4) · Hivemind **Shift
  Change** (action energy −25%) · Avian **Rooftop Lines** (walks half time)
  · Reptilian **Patient Metabolism** (statuses −1 turn, min 1) · Mycoid
  **Photosynthesis** (daylight wait/explore = +5 energy) · Luminal **The
  Tell** (double-edged: dialogue affection +1, offenses −1 worse) ·
  Substrate-Born **Native Signal** (+15 heat cap, Substrate entry half
  energy).
- **Selection**: registry species bring their trait automatically; a custom
  free-text species may claim ANY trait or none (creation-screen picker).
  Trait id persists on the player (migration 12), locked at creation.
  traits.effect(player, key, default) is the single resolution point; hooks
  live in actions/world/shop/combat/dungeon and the dialogue routes.
- **Species-flavored dialogue**: choices gain ``requires_trait`` (hidden from
  everyone else, like requires_event). Showcases: an Uplift line at Oona's
  lab-escape beat, a Substrate-Born line greeting Nyx. NOTE: default humans
  now ride transit free — old cost tests updated to use an untraited species.
- +17 pytest (333 total); all ten traits verified LIVE against the real
  server (one fresh save per trait), plus Playwright shots of the trait
  picker (auto for registry species, full chip list for custom).

### Follow-up: cyberpunk city — corps, markets, the fixer, the ripperdoc ✅ DONE
- **The Triumvirate** (`corps.json` + `game/corps.py`): Oceania Consolidated
  ("SAFETY IS FREEDOM" — surveillance that loves you), Eurasia Heavy
  Industries ("STRENGTH IS UNITY" — the people's muscle), Eastasia
  Transcendence ("THE SELF IS A DOOR" — premium ego-loss). Forever at "war":
  two allies vs one enemy, rotating weekly, each week declared eternal.
  Exactly the same at heart — every flagship ships from Plant 7. Street ads
  (new travel encounter kind) name-drop the current war. GET /api/corps.
- **Two cyberware markets**: The Triumvirate Exchange (Citadel Ring, 1.7×
  — cheap shelves are robbery, but the corp flagship augments are exclusive
  to it: PanOpt Suite, Atlas Frame, Ghostlace). The Static Bazaar (The Grid,
  0.55× — used chrome, honest prices, no receipts; discounted augments).
  Shop payloads carry a flavor blurb.
- **Mama Vex, the fixer** — the debt finally has a face. Full romanceable in
  the Docking Quarter back room (noon–2am). Her gig board (gigs.json,
  migration 10 `last_gig_day`): one gig a day, every gig forking clean
  (fair pay, sometimes a cast member approves) vs dirty (better pay + a
  moderate offense with someone who hears about it). GET /api/gigs,
  POST /api/gig; GigPanel UI.
- **Juno, the ripperdoc** — Second Skin clinic in The Grid: the
  transformation system's home. Full romanceable; her trust unlocks identity
  aspects (affection 15 → appearance, 25 → pronouns, 40 → body), and
  transforms now happen at the clinic (a place, never an identity gate —
  the paperwork is very forgiving). ClinicPanel UI with per-aspect editing.
- Intro dialogue trees for both. +13 pytest (259 total); verified live
  (dirty gig fork, both markets, unlock thresholds, clinic transform, ads).

### Follow-up: hacking — the casting stat ✅ DONE
- Seventh registry attribute: **hacking** ("how well your lace obeys").
  Trainable/visible/mirrored automatically; old saves gain it at 5.
- Strike protocols now swing with **lace power** (6 + level×2 + hacking×2)
  instead of your weapon-arm attack — courage builds punch, hacking builds
  cast. Shown as LACE on the equipment stats line.
- **Heat discipline**: every combat cast costs hacking//2 less heat (floor 5);
  the battle Protocol menu shows your true discounted costs.
- Flavor overrides: Zix hacks at 12 (wit 8), Nyx at 10 (charm 8).
  +2 pytest (243 total).
- **Augment capacity gate**: your lace syncs 1 augment + 1 per 5 hacking
  (hacking 15 runs all four slots; default 5 = two). Installing past capacity
  is refused with a train-it-higher error; swapping within an occupied slot
  is always allowed. Capacity shown on the equipment panel
  ("Augments synced: 2/2"). +3 pytest (246 total).

### Follow-up: status expansion + sexy attacks + Nyx (floor-10 NPC boss) ✅ DONE
- **Status registry** (`statuses.json`): all 14 effects data-driven (name/side/
  color/hint); battle chips render from it, no more hardcoded UI hints.
- **On you (the sexy ones)**: smitten (damage halved + 35% chance to lose your
  action admiring them; supersedes charm), marked (a lipstick burn — +25%
  damage taken), weak_knees (no dodge, crits falter), static_cling (−1
  charge/turn), drained (DoT that HEALS the enemy; the sip can't finish you).
  Element map: voltaic→static_cling, kinetic→weak_knees. Boss signatures:
  Contessa marks, Seraph smites, Empress drains.
- **On them / sexy player attacks**: new skills Blown Kiss (psionic, 40%
  entranced — no telegraphs or charged strikes), Hip Check (kinetic, 35%
  stagger — lose a turn; bosses immune, minibosses resist 50%), Static Touch
  (voltaic, 40% shock — attack −25%). New protocol Siren Overlay (guaranteed
  entrance, heat 35, epic boss-loot shard). Composure Spray (shop booster)
  cleanses the affection-family statuses.
- **Nyx, the Deep Signal** — floor-10 NPC boss (MAX_FLOOR now 10; the
  every-10th-floor pattern hangs off NPC_BOSS_UNLOCKS). Psionic boss with
  Undertow Kiss (drains) and Total Eclipse (smites), two phases. Beating her
  appends `defeated:nyx_deep_signal` to fired_events, which unlocks her
  characters.json entry (`requires_defeat` field, filtered everywhere via
  NPC.load_unlocked): she surfaces in The Shallows as a full romanceable —
  schedule, preferences, intro dialogue tree, psionic dps companion block,
  starting affection 10 ("she liked losing to you"). Victory screen announces
  the unlock. +19 pytest (241 total); verified live — she WON the first
  level-14 fight (drain sustain is real), fell to a guard-the-telegraph
  level-25 rematch, then chatted in the market.

### Follow-up: wetware protocols (magic) + augmentation slots ✅ DONE
- **Magic, sci-fi flavored**: protocols are forbidden code run on your neural
  lace, learned permanently by consuming data-shards (new item type, found in
  boss/miniboss loot, premium caches, and a few shops). Registry:
  `protocols.json`; player list persisted via migration 9.
- **Heat**: casting in combat builds heat (cap 100, vents 8/round). A cast
  that overflows the cap still fires but burns you with feedback (12% max HP)
  — can even kill you before the enemy moves. Heat gauge in the battle HUD.
- Combat protocols: Gravity Snap (2.2x kinetic), Time Stutter (enemy loses a
  turn), Mirror Ghost (+40% dodge, 2 turns), Purge Cycle (cleanse + heal),
  Overclock Lace (+2 charge, +3 attack for the fight). Utility (energy cost,
  out of combat): Cartographer's Dream (reveal floor), Phantom Hands (reveal
  concealed seams). Battle command menu gains a Protocol ▸ submenu; dungeon
  actions gain utility cast buttons.
- **Augmentation slots**: four new cyberware slots (neural/ocular/dermal/
  skeletal) riding the whole equipment engine — install/swap like gear, no
  gem sockets. Six augments: Reflex Splice (+2 spd, +5% dodge), Smartlink
  Eyes, Subdermal Plating, Myofiber Graft, Coolant Weave (+6 heat vent),
  Overclock Core (+40 heat cap). Equipment bonuses now aggregate dodge/
  heat_cap/heat_vent. +17 pytest (222 total); verified live (learn → install
  → map reveal → Time Stutter steals a turn at heat 37/140).

### Follow-up: agility & luck; speed→crit, agility→dodge ✅ DONE
- Two new registry attributes (zero-code additions elsewhere: StatBar, train
  action, and NPC mirroring all pick them up automatically; old saves gain
  them at default 5 via the registry merge on load).
- **Speed now matters**: crit chance = 5% + 0.5%/speed + 0.4%/luck (cap 35%).
  Enemies crit off their own speed stat (finally used). Companions keep the
  flat 10%.
- **Agility**: dodge = 1.5%/agi + 0.4%/luck (cap 30%) against enemy basic and
  charged strikes — telegraphed signatures can't be dodged (guard-reading
  stays their counter). Agility//2 also joins defense alongside wit//2.
- **Luck wired through the whole game**: crit + dodge contributions; flee
  window (+2%/pt, cap 90%); loot drop + jackpot chances (+3% relative/pt);
  treasure/cache/hoard credit payouts (+2%/pt); hidden-seam Search (+luck//3
  on the Wit check); job tips (luck%-chance ×3 of +5+luck cr, shown in the
  UI); travel encounter chance (+1%/pt).
- player_stats exposes crit/dodge (shown as % on the equipment panel).
  +13 pytest (205 total).

### Follow-up: FF7-style battle screen ✅ DONE
- Combat is now a wide modal popup (min(1080px, 96vw)) over the dungeon: party
  on the LEFT of the battlefield, enemy on the RIGHT, FF7-style message box up
  top (last 3 log lines, newest highlighted), telegraph banner below it.
- Battlefield: glowing circular "sprites" (player monogram, companion role
  icon, enemy glyph tinted by element with idle float; pulses red while a
  telegraphed move charges; guard shows a shield pip). Enemy HP bar + statuses
  + description under the sprite.
- Bottom HUD, FF7 menu boxes: command menu (left) with Skill ▸ / Item ▸
  SUBMENUS (cost + element / quantity shown), and a party status strip
  (right): name, HP bar (pulses red ≤25%), charge pips, statuses, DOWN tag.
- Victory fanfare: `finish_combat` now carries the rewards out of the battle
  state; a CombatOutcome modal (App-level, survives defeat ending the run)
  shows VICTORY + XP/credits/level-ups/drops/hoard, GOT AWAY, or DEFEAT with
  credits lost. Dungeon screen widened 720→920px. +6 vitest (15 total);
  verified in a live browser (battle, skill submenu, victory screens).

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
| Polish: real art, music, save/load UX, title | 7 | swap placeholders for assets; **UI grime** (NEXUS OS boot screen, scanline vignette, glitch-on-damage text, terminal title) |
| Night city rhythm | — | after-22:00 district shifts: night stock/prices, swapped encounter tables, night-only schedule windows |
| Memory economy | — | MAYBE: dungeon memory shards (dead delvers' last recordings, lore + a quiet questline) and a memory pawnshop (pawn discovered topics/affection history for credits, buy back with interest, cast reacts) |
| Street cred + battle arena | — | ✅ DONE — see The Pit above. Future: cred-gated black-market tiers, dialogue options, gig-earned cred |
| Corps differentiation pass | — | USER DIRECTION: the Triumvirate are NOT surface-identical — each corp is unique in aesthetic, product line, and voice; only *at heart* (money, power, extraction) are they the same. Rework blurbs/ads/flagships to distinct identities (e.g. Oceania=security/surveillance, Eurasia=heavy industry/body, Eastasia=media/mind); the Plant 7 gag survives only as buried conspiracy (same components inside all three flagships), not as identical storefronts |
| The Forget-Me-Not (pawnshop venue) | — | MAYBE: buys anything no questions (item selling), later the memory-economy storefront |
| The Better Devil (gambling barge venue) | — | MAYBE: luck-stat sink (dice/cards/wheel), runs a book on Pit fights — friction with Ondo |

### Follow-up: the Cyberlink (default integrated augment) ✅ DONE
- **The Cyberlink**: standard-issue neural interface, activated with the
  arrival paperwork ("also on your tab") — the diegetic home for the game's
  device layer. items.json entry with slot "integrated" (below the augment
  slots, uses no headroom, sold nowhere, value 0); shown on the equipment
  panel as "⬡ Cyberlink — integrated, standard issue"; the arrival story
  beat mentions it booting behind your ear.
- **Remote messaging** (game/cyberlink.py + data/messages.json + migration
  14: relationships.last_message_day): ping any cast member you've MET (one
  real conversation = the handshake) from anywhere, any hour, one per NPC
  per day, 5 min. Three tones — check in (+1), flirt (+2, needs
  acquaintance+ or you get that NPC's bespoke deflection), send something
  dumb (+1). Every cast member has a four-line authored texting voice (Zix
  answers from six bodies at once; Miko sends a four-second chord; Vex
  replies "checking on me or checking your balance, line item?"). Off-window
  contacts answer late ("the link sits quiet a while"). /api/message +
  /api/link/tones; characters payload gains met/messaged_today.
- **The Link modal** (⬡ Link in the HUD): Messages (contact list by stage +
  tone buttons + reply card), Inventory (panel moved off the map screen into
  the device where it belongs), Settings (difficulty + unit summary:
  name/pronouns/species/trait + the EULA nobody read). +9 pytest (356
  total, incl. an every-NPC-has-a-voice integrity test); verified live
  (handshake refusal, remote ping, per-day gate) + Playwright shots.
- NOTE found while testing: Carro (disposition −5) has no dialogue tree
  until affection ≥ 0 — talking to him day one 404s ("nothing to say yet").
  Possibly intended (gift the grumpy lizard first); flagging for review.

## Venue Roadmap (approved, build one at a time)

Five venues approved 2026-07-15; detailed plans agreed in-session. Suggested
order (each independently shippable):

1. ✅ **The Night Market** (Bloom District, 18:00–04:00) — DONE. First
   night-only venue: venue-keyed shop, 3 stalls rotating nightly from a
   12-item pool (deterministic by absolute day — `shop.rotating_ids`,
   "✶ tonight only" badges, buyable only on their night), four street foods
   (Skewered Something / Glow Broth / Static Floss / Vendor's Mercy), and
   **gossip**: once a night (migration 13: gossip_day), a vendor names a
   cast member's real preference lean in rumor-speak — true, but never
   marked discovered. Nyx's evening window moved to the market's stalls.
   Loot integrity tests sweep rotation pools too.
   **Shipped alongside (same commit): transportation + homes.**
   - **Tubes AND cabs** (user decision): transit is canonically the Loop
     (mag-tube ring; Priced In rides free); new third mode `cab` — hovercab,
     door to door, any place incl. straight to a venue, flat 6 min /
     −2 energy / 30 cr, never free. Night surge deferred to night-rhythm.
   - **Homes + full schedules**: every NPC has a home block ({name, blurb};
     Vex "Above the bar — nobody has ever seen the inside", Oona's brine
     tank, Ondo's cot in the aft locker room…), availability now carries the
     window's activity, and the People panel shows off-hours life ("Asleep ·
     The Hideout Annex"). Integrity tests: everyone housed, every schedule
     covers all 1440 minutes.
2. **Gantry 9** (The Grid, always open) — rooftop-line terminus teahouse.
   The Lookout: a server-composed almanac (who's reachable where right now,
   what's open, this week's corp war, today's gig, tonight's Pit card). Tea
   service = small timed buff. Avian trait flavors the entry line (never
   gates). Mostly a read-model + panel; smallest build.
3. **The Stacks** (Citadel Ring, 24h) — archive-library. House rates for
   Wit/Hacking (mirror of the Hold). Research desk: spend time+energy to
   pull a file on a known NPC (reveals one undiscovered preference; slower
   but surer than gifting blind). Home of **Index**, the ghost archivist —
   the design doc's imperceivable energy being: present from day one but
   unlockable via perception (a findable item for everyone; Substrate-Born
   perceive them natively — species opens the door early, never exclusively).
   New NPC-unlock kind: requires_perception.
4. **The Steeps** (Bloom District, 10:00–02:00) — bathhouse in a dead cooling
   tower. THE DATING SYSTEM: invite a reachable NPC on an outing (venue-keyed
   scenes in dates.json, choice beats, big affection, once per NPC per week).
   Also: paid soak = full rest + status cleanse in 90 min. Dates generalize
   to Night Market/Gantry 9 afterwards.
5. **The Tide Line** (Docking Quarter, open 04:00–06:00 only) — flooded
   maintenance levels. Salvage-run venue (small event table: finds, hazards,
   rare curio), and Ondo's dawn walk made real: meeting them down there
   (they said "Don't") opens dialogue ringside can't — keyed to affection,
   deepening their arc.

**Transportation (decision pending):** proposal = make "transit" diegetically
**the Loop** (pneumatic mag-tube ring; fits the ring-of-districts map) and add
a third mode, **hovercab**: anywhere→anywhere incl. straight to a venue door,
flat ~6 min, expensive (~30 cr, night surge) — pairs with a future Loop
maintenance window (02:00–05:00) under the night-rhythm milestone. Ferries in
the Shallows stay flavor. Priced In covers the Loop, not hovercabs.

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
