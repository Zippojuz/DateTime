# NEXUS CITY — Game Design Document
*A Sci-Fi Dating Sim / JRPG*
 
---
 
## Overview
 
You play as a drifter who lands in Nexus City with nothing but a ship and a debt to pay off. You take jobs, explore the city, get tangled in the lives of its residents — and maybe fall in love along the way.
 
**Stack:** Flask (Python backend) + React (frontend)
**Save system:** SQLite
 
---
 
## The World — Nexus City
 
A massive interstellar hub city built on (or possibly *as*) a space station the size of a metropolis.
 
### Districts
 
| District | Vibe | Hours |
|---|---|---|
| **The Docking Quarter** | Seedy bars, shady merchants, the docks never close | Bars 18:00–04:00 / Docks 24hrs |
| **The Bloom District** | Alien flora, upscale, diplomatic types | Shops 09:00–18:00 / Gardens 06:00–21:00 |
| **The Grid** | Tech/hacker district, neon, underground clubs | Clubs 20:00–05:00 / Tech shops 10:00–22:00 |
| **The Citadel Ring** | Government, military, bureaucrats | Offices 08:00–17:00 / Plaza 24hrs |
| **The Shallows** | Lower city, working class, markets, danger | Market 05:00–20:00 / Music venues 19:00–02:00 |
 
---
 
## Player Character
 
Fully customizable: name, pronouns, species, appearance.
 
### Player Stats
 
| Stat | Affects |
|---|---|
| **Charm** | Dialogue options, affection gains |
| **Wit** | Puzzle/hacking outcomes, certain dialogue |
| **Courage** | Combat, risky dialogue choices |
| **Empathy** | Unlocking deeper character routes |
 
---
 
## Alien Species
 
### Design Questions (Open)
- How alien do we go? Mix of humanoid-leaning and genuinely strange is the current direction
- Should species have mechanical implications? (perception abilities, unique interactions) — leaning yes
- Player species being unknown may tie into hidden abilities they don't yet understand
- Romance characters' species affects *how* you interact with them mechanically
### Humanoid-ish Species
 
| Concept | Biology | Cultural Flavor |
|---|---|---|
| **Bioluminescent tall beings** | Glow patterns communicate emotion involuntarily — can't hide their feelings | Warrior culture, honor-bound |
| **Small multi-limbed tinkerers** | 4–6 arms, big eyes, fast metabolism | Hacker/engineer class, chaotic energy |
| **Feathered avian species** | Hollow bones, expressive plumage, physically incapable of convincing lying | Artistic, passionate, dramatic |
| **Reptilian cold-bloods** | Scales, nictitating eyes, slow to trust but fiercely loyal | Merchant class, long memories |
| **Plant-fungal hybrids** | Partially photosynthetic, release spores when emotional | Pacifist, ancient knowledge, deeply empathic |
 
### Weird Middle Ground
 
| Concept | Biology | Cultural Flavor |
|---|---|---|
| **Hivemind colony** | Multiple small bodies forming one consciousness | Deeply communal, find solitude terrifying |
| **Crystalline beings** | Silicon-based, grow slowly, potentially ancient | Speak in harmonic tones, very literal |
| **Gaseous species in containment suits** | True form is a colored cloud — suits are fashion statements | What they choose to look like says everything about them |
| **Aquatic out-of-water** | Breathe through gill-collars, skin must stay moist | Adapted to city life but always slightly uncomfortable |
| **Shade-dwellers** | Photosensitive, only come out at night | Dominate the late-night economy, mysterious to day-walkers |
 
### Genuinely Strange
 
| Concept | Biology | Cultural Flavor |
|---|---|---|
| **Time-fractured beings** | Experience past/present/future simultaneously | Conversations feel cryptic until you understand them |
| **Gravity shapers** | No fixed form, manipulate local gravity to move | Don't walk — drift and pull |
| **Memory eaters** | Feed on psychic impressions — not malicious, it's just eating | Complicated relationship with the rest of the city |
| **Echo beings** | Exist slightly out of phase — you see their afterimage before they arrive | Communication has a natural delay |
| **Gestalt architecture** | Bodies are partially the buildings they inhabit | Some districts ARE their residents |
 
---
 
## The Cast — Romanceable Characters
 
All characters are romanceable regardless of player identity.
 
| Name | Species | Personality | District | Arc Theme |
|---|---|---|---|---|
| **Vael** | Bioluminescent tall being | Stoic soldier, guarded | Citadel Ring | Learning to trust again |
| **Zix** | Hivemind colony | Chaotic hacker, witty | The Grid | Running from their past |
| **Sora** | Plant-fungal hybrid | Gentle botanist, wise | Bloom District | Belonging vs. duty |
| **Carro** | Reptilian cold-blood | Slick merchant, morally grey | Docking Quarter | Redemption |
| **Miko** | Feathered avian | Rebel musician, passionate | The Shallows | Finding their voice |
 
### Why These Species Fit
- **Vael** — glow patterns betray emotions, making their "stoic soldier" persona dramatically ironic
- **Zix** — which part of the hivemind likes you? Win them over one body at a time
- **Sora** — releases spores when flustered; impossible to hide feelings around someone they like
- **Carro** — reptilian long memory means they remember every kindness and every slight equally
- **Miko** — plumage displays involuntarily during performances; excitement is visible to everyone
### Example Character Schedules
 
**Vael**
- 06:00–08:00 — Morning training, Citadel Ring gym
- 08:00–17:00 — On duty, Citadel offices (unavailable)
- 17:00–19:00 — Decompressing at the Citadel plaza
- 19:00–22:00 — Dinner alone at a quiet restaurant
- 22:00+ — Home / unavailable
**Zix**
- 00:00–11:00 — Asleep (sleeps late)
- 11:00–14:00 — Wandering The Grid, grabbing food
- 14:00–19:00 — Working from their hideout (findable)
- 19:00–03:00 — At the clubs or causing trouble
- 03:00+ — Home / unavailable
---
 
## Time System
 
### The 24-Hour Clock
 
The clock only moves when the player commits to an action. It pauses during menus and planning.
 
### Travel
 
Travel between districts takes real time and is a source of random encounters.
 
| Route | Walk | Transit (costs credits) |
|---|---|---|
| Adjacent districts | 15–20 min | 5–10 min |
| Cross-city | 30–45 min | 15–20 min |
 
### Activity Time Costs
 
| Activity | Time Cost |
|---|---|
| Sleep (full rest) | 8 hrs |
| Quick nap | 2 hrs |
| Grab food at a stall | 30 min |
| Sit-down restaurant | 1.5 hrs |
| Short job | 2 hrs |
| Long job | 4–6 hrs |
| Casual hangout with character | 2 hrs |
| Deep conversation / date | 3–4 hrs |
| Explore a district | 1–3 hrs |
| Train a stat | 2 hrs |
| Shopping | 1 hr |
| Attending an event | Fixed duration |
 
### Arriving Late
 
If you arrive near the end of a character's availability window:
 
| Time Remaining | Outcome |
|---|---|
| 60+ min | Full interaction available |
| 30–59 min | Shortened scene, less affection gain, unique "rushed" dialogue |
| 10–29 min | Brief exchange only, small affection gain |
| 0–9 min | Just missed them — a note or glimpse, no affection but a story moment |
 
### Energy System
 
| Action | Energy |
|---|---|
| Full night's sleep | Restores to 100% |
| Nap | +30% |
| Intense job | -30 |
| Casual hangout | -15 |
| Exploring | -10 per hour |
| Eating a meal | +20 |
| Drinking at a bar | -10 (but +mood?) |
 
Low energy locks out some dialogue options and makes stat checks harder.
 
---
 
## Random Street Encounters
 
Occur during travel. No time cost unless they escalate.
 
- **Flavor encounters** — world-building moments, no consequence
- **Character sightings** — brief exchange with a romance character, tiny affection bump
- **Traveling merchant** — rare vendor, optional 30 min to browse
- **Trouble** — moral choice (intervene or walk past), no time cost
- **Quest starters** — can accept (time cost, quest begins) or defer (saved in log for later)
---
 
## The Calendar
 
- Game runs over one in-game year (52 weeks)
- Seasonal events — city festivals, story beats, character birthdays
- Some romance milestones are time-gated — miss them and wait for next cycle or replay
---
 
## Weird Ideas — To Explore
 
### Characters
 
- **Hivemind alien "Keth"** — actually 6 small creatures forming a humanoid shape. Each has their own feelings toward the player. Track affection for each individual — they don't always agree. Win them over one by one.
- **Time-displaced alien** — experiences time non-linearly. Already knows how your relationship ends. Their dialogue references things that haven't happened yet. Do they love who you are now, or who you'll become?
- **Corporate AI** — built to manage a megacorp district. Technically property, not a person. Romance route involves fighting for their legal personhood alongside the relationship.
- **A ghost** — an energy being most species can't perceive. Requires special equipment or species ability to detect. Half the city doesn't believe they exist. Dates are logistically interesting.
- **Your ship's AI** — has been with you longer than anyone. Slow burn. Has been quietly developing feelings for years. The route is about whether you notice.
### Mechanics
 
- **Reputation is double-edged** — fame opens doors but attracts stalkers, con artists, and political enemies who sabotage your relationships.
- **The city has a dark secret** — partway through the year, something is wrong. Disappearances. Strange signals. The dating sim layer develops a horror tinge. People you love are in danger.
- **Unreliable memory** — the player character has gaps in their past. Why did they really come to Nexus City? Late game revelations recontextualize early scenes.
- **Relationship bleed** — characters talk to each other. Jealousy is a real mechanic. Playing the field has social consequences within the cast.
- **The debt has teeth** — someone powerful is owed. As the year progresses, pressure mounts. Who you've built relationships with determines who can help when it comes due.
### World
 
- **Nexus City is a living organism** — the station is an ancient alien creature. It has moods. Districts behave differently on bad days. Some characters know. Most don't.
- **Species perceive time differently** — some NPCs age visibly over the in-game year. One character you meet early is ancient but looks young. Another is young but looks old.
- **The player's species is unknown** — even to them. Different aliens react with unexplained familiarity or fear. A mystery unraveled across romance routes.
### Narrative
 
- **Multiple true endings that contradict each other** — each romance route reveals a different "true" version of what Nexus City is and why you're there.
- **A romance route with the city itself** — through recurring encounters with a mysterious stranger, you realize you're developing feelings for a manifestation of Nexus City's collective consciousness.
- **A character who is romancing you** — one NPC has been actively pursuing the player from day one. You can lean in, let them down, or discover their motives are more complicated than affection.
---
 
## Tech Architecture
 
```
my_jrpg/
├── backend/                  # Python / Flask
│   ├── app.py
│   ├── game/
│   │   ├── battle.py
│   │   ├── player.py
│   │   ├── world.py
│   │   ├── social.py
│   │   ├── calendar.py
│   │   ├── dialogue.py
│   │   └── crafting.py
│   └── data/
│       ├── characters.json
│       ├── enemies.json
│       ├── items.json
│       └── events.json
│
└── frontend/                 # React
    └── src/
        ├── screens/
        │   ├── BattleScreen.jsx
        │   ├── WorldMap.jsx
        │   ├── DialogueScreen.jsx
        │   ├── CalendarScreen.jsx
        │   └── MenuScreen.jsx
        └── components/
            ├── StatBar.jsx
            ├── SkillTree.jsx
            ├── Inventory.jsx
            └── RelationshipPanel.jsx
```
 
---
 
## Art & Asset Strategy
 
### Philosophy
Ship with placeholder art first. Get the systems feeling good, then drop in real art. Every good indie game did this.
 
### Placeholder Approach (Phase 1–3)
- Colored boxes for character portraits
- Solid color backgrounds with location name text
- CSS-built UI — no art assets needed at all
- Focus entirely on systems and writing
### Character Portraits
The best option for unique alien designs that no asset pack will have:
 
| Tool | Cost | Notes |
|---|---|---|
| **Midjourney** | Paid (cheap) | Best quality, most control |
| **Leonardo.ai** | Free tier available | Good for consistent character style |
| **Bing Image Creator** | Free | Solid for quick concepts |
| **itch.io VN sprite packs** | Free–cheap | Pre-made, faster but less unique |
 
For alien characters especially, AI generation wins — you can describe exactly what you want ("tall bioluminescent alien, humanoid, soldier armor, glowing blue skin patterns, sci-fi visual novel style") and get something no asset pack has.
 
Consistency tip: save your prompts. Reuse the same base prompt with small variations to keep a character looking like themselves across different expressions/poses.
 
### Backgrounds & Scenes
| Source | Best For |
|---|---|
| **itch.io sci-fi background packs** | District scenes, interiors |
| **AI generation** | Specific locations (Zix's hideout, Sora's garden) |
| **OpenGameArt.org** | CC-licensed free options |
 
Search terms that work well: "cyberpunk space station interior", "neon alien city market", "sci-fi bar night"
 
### Walking Character Sprite (if implemented)
| Source | Style |
|---|---|
| **LPC assets on OpenGameArt** | Top-down RPG, Stardew-like, huge free library |
| **itch.io "top down character"** | Many free packs |
| **CSS animated div** | Simplest possible — a colored shape that moves |
 
### UI Elements
Build entirely in React/CSS — no assets needed. The UI should feel clean and sci-fi: dark backgrounds, neon accent colors, clean typography.
 
### Adult Content Art
If the game goes explicit:
- Gate behind relationship progression milestones
- AI generation works for written descriptions to accompany
- Illustrated scenes are expensive to commission — consider written-only for v1
- itch.io is the right distribution platform (allows adult content with age gate)
- Steam requires a separate adult patch submitted after base game approval
### Asset Folder Structure
```
frontend/
└── public/
    └── assets/
        ├── characters/
        │   ├── vael/
        │   │   ├── vael_neutral.png
        │   │   ├── vael_happy.png
        │   │   ├── vael_angry.png
        │   │   └── vael_flustered.png
        │   └── zix/ ...
        ├── backgrounds/
        │   ├── docking_quarter_day.png
        │   ├── docking_quarter_night.png
        │   └── ...
        ├── ui/
        │   └── (icons, buttons, frames)
        └── music/
            └── (placeholder or CC tracks)
```
 
Each romance character should have at minimum 4 expression variants: neutral, happy, sad/hurt, flustered. More expressions unlock with relationship progression.
 
---
 
## Build Phases
 
| Phase | Focus |
|---|---|
| 1 | Player creation, basic calendar, daily action loop |
| 2 | One character fully implemented (dialogue tree, affection system) |
| 3 | All 5 characters stubbed, city districts explorable |
| 4 | Story events, seasonal calendar, jobs system |
| 5 | Combat system (TBD how it integrates) |
| 6 | Crafting, gifting, full relationship arcs |
| 7 | Polish — art, music, save/load, title screen |
 
---
 
*Document last updated: planning session 3 — art & asset strategy added*
