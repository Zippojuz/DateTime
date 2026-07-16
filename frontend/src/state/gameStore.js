import { create } from 'zustand'
import { api } from '../api/client'

// The single authoritative client-side store. Because the backend is
// server-authoritative, this store mirrors state fetched from the API rather
// than owning game rules itself.
export const useGameStore = create((set, get) => ({
  // Connection: 'unknown' | 'ok' | 'error'
  connection: 'unknown',
  connectionError: null,

  // Screen: 'loading' | 'title' | 'creation' | 'play'
  screen: 'loading',

  // Reference data (rendered generically).
  attributes: null, // registry: { id: {name, description, ...} }
  actions: null, // { id: {label, minutes, energy, ...} }
  topics: null, // registry: { id: {name, changeable} }
  districts: null, // registry: { id: {name, vibe, adjacent} }
  venues: null, // registry: { id: {name, district, vibe, hours} } — places inside districts
  species: null, // registry: { id: {name, blurb} } — creation suggestions, never gates
  items: null, // registry: { id: {name, type, rarity, ...} }
  protocols: null, // registry: { id: {name, kind, heat|energy, ...} }
  statuses: null, // registry: { id: {name, side, color, hint} }

  // Shop stock for the current place; gift flow + last reaction.
  shop: null,
  lastGossip: null, // last Night Market rumor: { npc, topic, text }

  // The Cyberlink (standard-issue neural interface): device modal + messages.
  linkOpen: false,
  linkTones: null, // { id: {label, affection, requires_stage?} }
  lastMessage: null, // last reply: { npc, reply, landed, gained, affection }
  gifting: null, // { npcId, npcName } while picking a gift
  lastReaction: null, // last gift reaction toast

  // The most recent travel encounter, shown then dismissed.
  lastEncounter: null,

  // Current game state from the server: { player, clock }
  state: null,
  hasSave: false,

  // Characters with availability + affection, refreshed as the clock moves.
  characters: [],

  // Jobs (with reachability), refreshed as location changes.
  jobs: [],
  lastJob: null, // last job result: { job, pay, bonus }

  // Mama Vex's daily gig: { gig, done_today, reachable }
  gigs: null,
  lastGig: null, // last gig result: { text, pay }

  // Seasonal events waiting to be acknowledged.
  pendingEvents: [],

  // Active dialogue: null | { npcId, npcName, tier, node, lastGained }
  dialogue: null,

  // The Substrate: { run, combat, stats, skills, xp_to_next } from the server,
  // plus the last room/outcome result for display.
  dungeon: null,
  dungeonResult: null,
  difficulties: null,

  // Gear loadout: { slots, slot_order, bonuses, stats } from the server.
  equipment: null,

  // Party: { companion, required_affection, candidates } from the server.
  party: null,

  // The Pit: { name, wins, titles, street_cred, cred_stage, next } from the server.
  arena: null,

  // Gantry 9: tea service { menu, active, sipped_today } + the Lookout board.
  teahouse: null,
  lookout: null,
  lastPour: null,

  // The Stacks: research desk { minutes, energy, researched_today, draft }.
  stacks: null,
  lastResearch: null,

  // THE DATING SYSTEM: the venue menu, the ask-out picker, the live scene.
  dateVenues: null,
  askOut: null, // {npcId, name} while the venue picker is open
  date: null, // the active beat / closing view from the server
  lastSoak: null,

  busy: false,
  error: null,

  // Load reference data + any existing save. Called once on mount.
  init: async () => {
    try {
      const [
        attributes,
        actions,
        topics,
        districts,
        venues,
        species,
        items,
        protocols,
        statuses,
        linkTones,
        dateVenues,
      ] = await Promise.all([
        api.attributes(),
        api.actions(),
        api.topics(),
        api.districts(),
        api.venues(),
        api.species(),
        api.items(),
        api.protocols(),
        api.statuses(),
        api.linkTones(),
        api.dateVenues(),
      ])
      set({
        attributes,
        actions,
        topics,
        districts,
        venues,
        species,
        items,
        protocols,
        statuses,
        linkTones,
        dateVenues,
        connection: 'ok',
      })
    } catch (err) {
      set({ connection: 'error', connectionError: err.message, screen: 'title' })
      return
    }

    try {
      const state = await api.getState()
      set({ state, hasSave: true, screen: 'title' })
    } catch (err) {
      if (err.status === 404) {
        set({ hasSave: false, screen: 'title' })
      } else {
        set({ connection: 'error', connectionError: err.message, screen: 'title' })
      }
    }
  },

  startCreation: () => set({ screen: 'creation', error: null }),
  continueGame: () => {
    if (get().state) {
      set({ screen: 'play' })
      get().loadCharacters()
      get().loadJobs()
      get().loadGigs()
      get().loadShop()
      get().loadDungeon() // resume a mid-run Substrate dive
      get().loadEquipment()
      get().loadParty()
      get().loadArena()
      get().loadTeahouse()
      get().loadLookout()
      get().loadStacks()
    }
  },

  newGame: async (identity) => {
    set({ busy: true, error: null })
    try {
      // Response is {player, clock, events} (events kept separate from state).
      const { events, ...state } = await api.newGame(identity)
      set({ state, hasSave: true, screen: 'play', busy: false })
      get()._pushEvents(events)
      get().loadCharacters()
      get().loadJobs()
      get().loadGigs()
      get().loadShop()
      get().loadDungeon()
      get().loadEquipment()
      get().loadParty()
      get().loadArena()
      get().loadTeahouse()
      get().loadStacks()
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  loadCharacters: async () => {
    try {
      const characters = await api.characters()
      set({ characters })
    } catch {
      // Non-fatal — the daily loop still works without the People panel.
    }
  },

  loadJobs: async () => {
    try {
      set({ jobs: await api.jobs() })
    } catch {
      // Non-fatal.
    }
  },

  loadGigs: async () => {
    try {
      set({ gigs: await api.gigs() })
    } catch {
      // Non-fatal.
    }
  },

  workGig: async (gigId, choiceIndex) => {
    set({ busy: true, error: null })
    try {
      const res = await api.workGig(gigId, choiceIndex)
      set({ state: res.state, lastGig: res.result, busy: false })
      get()._pushEvents(res.events)
      get().loadGigs()
      get().loadCharacters() // gigs move opinions — cleanly or otherwise
      get().loadShop() // dirty-gig cred can open black-market back rooms
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  transform: async (changes) => {
    set({ busy: true, error: null })
    try {
      const state = await api.transform(changes)
      set({ state, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  _pushEvents: (evs) => {
    if (evs && evs.length) {
      set((s) => ({ pendingEvents: [...s.pendingEvents, ...evs] }))
    }
  },
  dismissEvent: (id) =>
    set((s) => ({ pendingEvents: s.pendingEvents.filter((e) => e.id !== id) })),

  workJob: async (jobId) => {
    set({ busy: true, error: null })
    try {
      const res = await api.work(jobId)
      set({ state: res.state, lastJob: res.result, busy: false })
      get()._pushEvents(res.events)
      get().loadCharacters()
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  payDebt: async (amount) => {
    set({ busy: true, error: null })
    try {
      const res = await api.payDebt(amount)
      set({ state: res.state, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  loadShop: async () => {
    try {
      set({ shop: await api.shop() })
    } catch {
      // Non-fatal.
    }
  },

  openLink: () => set({ linkOpen: true, error: null }),
  closeLink: () => set({ linkOpen: false, lastMessage: null }),

  sendMessage: async (npcId, tone) => {
    set({ busy: true, error: null })
    try {
      const res = await api.sendMessage(npcId, tone)
      set({ state: res.state, lastMessage: res.message, busy: false })
      get().loadCharacters() // affection + the per-day ping gate moved
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  marketGossip: async () => {
    set({ busy: true, error: null })
    try {
      const res = await api.marketGossip()
      set({
        lastGossip: res,
        ...(res.state ? { state: res.state } : {}),
        busy: false,
      })
      get().loadShop() // the ask-around button burns for the night
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  buyItem: async (itemId) => {
    set({ busy: true, error: null })
    try {
      const res = await api.buy(itemId)
      set({ state: res.state, busy: false })
      get()._pushEvents(res.events)
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  useItem: async (itemId) => {
    set({ busy: true, error: null })
    try {
      const res = await api.useItem(itemId)
      set({ state: res.state, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  startGift: (npcId, npcName) => set({ gifting: { npcId, npcName }, error: null }),
  cancelGift: () => set({ gifting: null }),

  giveGift: async (itemId) => {
    const g = get().gifting
    if (!g) return
    set({ busy: true, error: null })
    try {
      const res = await api.gift(g.npcId, itemId)
      set({
        state: res.state,
        gifting: null,
        lastReaction: { ...res.reaction, npcName: g.npcName },
        busy: false,
      })
      get().loadCharacters() // affection + discovered prefs changed
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  dismissReaction: () => set({ lastReaction: null }),

  // --- The Substrate (dungeon + combat) ---

  loadDungeon: async () => {
    try {
      const [dungeon, difficulties] = await Promise.all([
        api.dungeonState(),
        api.difficulties(),
      ])
      set({ dungeon, difficulties })
    } catch {
      // Non-fatal.
    }
  },

  enterDungeon: async () => {
    set({ busy: true, error: null })
    try {
      const res = await api.dungeonEnter()
      set({ dungeon: res, state: res.state, dungeonResult: null, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  _dungeonAction: async (call) => {
    set({ busy: true, error: null })
    try {
      const res = await call()
      set({ dungeon: res, state: res.state, dungeonResult: res.result, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  moveDungeon: (dir) => get()._dungeonAction(() => api.dungeonMove(dir)),
  searchDungeon: () => get()._dungeonAction(() => api.dungeonSearch()),
  interactDungeon: () => get()._dungeonAction(() => api.dungeonInteract()),
  curioAct: (curioId, verb) => get()._dungeonAction(() => api.dungeonCurio(curioId, verb)),
  castProtocol: (protocolId) => get()._dungeonAction(() => api.dungeonProtocol(protocolId)),

  chooseDungeonEvent: async (choiceIndex) => {
    set({ busy: true, error: null })
    try {
      const res = await api.dungeonEvent(choiceIndex)
      set({ dungeon: res, state: res.state, dungeonResult: res.result, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  leaveDungeon: async () => {
    set({ busy: true, error: null })
    try {
      const res = await api.dungeonLeave()
      set({ dungeon: res, state: res.state, dungeonResult: null, busy: false })
      get().loadCharacters() // delving together builds the bond
      get().loadParty()
      get().loadShop() // depth-record cred can open black-market back rooms
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  combatAct: async (action, extra = {}) => {
    set({ busy: true, error: null })
    try {
      const res = await api.combatAction({ action, ...extra })
      set({
        dungeon: res,
        state: res.state,
        dungeonResult: res.outcome ? { type: 'combat', ...res.outcome } : get().dungeonResult,
        busy: false,
      })
      if (res.outcome?.result === 'defeat') {
        get().loadCharacters() // going down together still deepens the bond
      }
      if (res.outcome?.unlocked) {
        get().loadCharacters() // someone new just surfaced
        get().loadParty()
      }
      if (res.outcome?.arena) {
        get().loadArena() // the ladder moved (or didn't)
        get().loadShop() // cred can open black-market back rooms
      }
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  clearDungeonResult: () => set({ dungeonResult: null }),

  setDifficulty: async (level) => {
    set({ busy: true, error: null })
    try {
      const state = await api.setDifficulty(level)
      set({ state, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  // --- Equipment & gems ---

  loadEquipment: async () => {
    try {
      set({ equipment: await api.equipment() })
    } catch {
      // Non-fatal.
    }
  },

  _equipmentAction: async (call) => {
    set({ busy: true, error: null })
    try {
      const res = await call()
      set({ equipment: res, state: res.state, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  equipItem: (itemId, slot) => get()._equipmentAction(() => api.equip(itemId, slot)),
  unequipSlot: (slot) => get()._equipmentAction(() => api.unequip(slot)),
  socketGem: (slot, gemId, index) =>
    get()._equipmentAction(() => api.socketGem(slot, gemId, index)),
  unsocketGem: (slot, index) => get()._equipmentAction(() => api.unsocketGem(slot, index)),

  // --- Party (one dungeon companion at a time) ---

  loadParty: async () => {
    try {
      set({ party: await api.party() })
    } catch {
      // Non-fatal.
    }
  },

  // --- The Pit (arena ladder) ---

  loadArena: async () => {
    try {
      set({ arena: await api.arena() })
    } catch {
      // Non-fatal.
    }
  },

  // --- Gantry 9 (tea service + the Lookout) ---

  loadTeahouse: async () => {
    try {
      set({ teahouse: await api.teahouse() })
    } catch {
      // Non-fatal.
    }
  },

  loadLookout: async () => {
    // The board hangs at the gantry — anywhere else there's nothing to fetch.
    if (get().state?.player?.location !== 'gantry_9') {
      set({ lookout: null })
      return
    }
    try {
      set({ lookout: await api.lookout() })
    } catch {
      // Non-fatal.
    }
  },

  sipTea: async (teaId) => {
    set({ busy: true, error: null })
    try {
      const res = await api.sipTea(teaId)
      set({ state: res.state, lastPour: res.poured, busy: false })
      get().loadTeahouse()
      get().loadLookout() // twenty minutes pass; the board moves
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  // --- The Stacks (research desk) ---

  loadStacks: async () => {
    try {
      set({ stacks: await api.stacks() })
    } catch {
      // Non-fatal.
    }
  },

  researchFile: async (subject) => {
    set({ busy: true, error: null })
    try {
      const res = await api.research(subject)
      set({ state: res.state, lastResearch: res.research, busy: false })
      get().loadStacks()
      get().loadCharacters() // a marked discovery — or someone new in the room
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  // --- The Steeps (soak) + THE DATING SYSTEM ---

  takeSoak: async () => {
    set({ busy: true, error: null })
    try {
      const res = await api.soak()
      set({ state: res.state, lastSoak: res.soak, busy: false })
      get().loadCharacters() // ninety minutes pass
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  openAskOut: (npcId, name) => set({ askOut: { npcId, name }, error: null }),
  closeAskOut: () => set({ askOut: null, error: null }),

  startDate: async (npcId, venue) => {
    set({ busy: true, error: null })
    try {
      const res = await api.dateStart(npcId, venue)
      set({ date: res.date, state: res.state, askOut: null, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  chooseDateBeat: async (choiceIndex) => {
    set({ busy: true, error: null })
    try {
      const res = await api.dateChoose(choiceIndex)
      set({ date: res.date, state: res.state, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  leaveDate: async () => {
    set({ busy: true, error: null })
    try {
      const res = await api.dateLeave()
      set({ date: res.date, state: res.state, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  closeDate: () => {
    set({ date: null })
    get().loadCharacters() // the evening moved hearts and hands of the clock
    get().loadShop()
    get().loadArena()
    get().loadTeahouse()
    get().loadStacks()
    get().loadLookout()
  },

  arenaFight: async () => {
    set({ busy: true, error: null })
    try {
      const res = await api.arenaFight()
      set({ dungeon: res, state: res.state, dungeonResult: null, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  recruitCompanion: async (npcId) => {
    set({ busy: true, error: null })
    try {
      const res = await api.recruit(npcId)
      set({ state: res.state, busy: false })
      get().loadParty()
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  dismissCompanion: async () => {
    set({ busy: true, error: null })
    try {
      const res = await api.dismissCompanion()
      set({ state: res.state, busy: false })
      get().loadParty()
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  doAction: async (action, attribute) => {
    set({ busy: true, error: null })
    try {
      // Response is {player, clock, events} (events kept separate from state).
      const { events, ...state } = await api.action({ action, attribute })
      set({ state, busy: false })
      get()._pushEvents(events)
      get().loadCharacters() // availability changes as the clock advances
      get().loadGigs()
      get().loadArena() // the Pit's doors track the clock
      get().loadTeahouse() // tea expires at midnight
      get().loadLookout() // the board tracks the whole clock
      get().loadStacks() // the desk reopens at midnight
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  travel: async (to, mode) => {
    set({ busy: true, error: null })
    try {
      const res = await api.travel(to, mode)
      set({ state: res.state, lastEncounter: res.encounter, busy: false })
      get()._pushEvents(res.events)
      get().loadCharacters() // reachability changes with location + time
      get().loadJobs()
      get().loadGigs()
      get().loadShop()
      get().loadArena() // open state + bell line track the clock and your record
      get().loadTeahouse()
      get().loadLookout() // only composes at Gantry 9
      get().loadStacks()
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  dismissEncounter: () => set({ lastEncounter: null }),

  startDialogue: async (npcId) => {
    set({ busy: true, error: null })
    try {
      const d = await api.dialogueStart(npcId)
      set({
        dialogue: {
          npcId,
          npcName: d.npc_name,
          dialogueId: d.dialogue_id,
          tier: d.tier,
          node: d.node,
          lastGained: 0,
        },
        busy: false,
      })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  chooseDialogue: async (choiceIndex) => {
    const dlg = get().dialogue
    if (!dlg) return
    set({ busy: true, error: null })
    try {
      const res = await api.dialogueChoose(
        dlg.npcId,
        dlg.dialogueId,
        dlg.node.node_id,
        choiceIndex,
      )
      if (res.ended) {
        set({ dialogue: null, busy: false })
        get().loadCharacters() // affection updated
      } else {
        set({
          dialogue: { ...dlg, node: res.node, lastGained: res.gained },
          busy: false,
        })
      }
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  closeDialogue: () => set({ dialogue: null }),
}))
