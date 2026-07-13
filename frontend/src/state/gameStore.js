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

  // Seasonal events waiting to be acknowledged.
  pendingEvents: [],

  // Active dialogue: null | { npcId, npcName, tier, node, lastGained }
  dialogue: null,

  busy: false,
  error: null,

  // Load reference data + any existing save. Called once on mount.
  init: async () => {
    try {
      const [attributes, actions, topics, districts] = await Promise.all([
        api.attributes(),
        api.actions(),
        api.topics(),
        api.districts(),
      ])
      set({ attributes, actions, topics, districts, connection: 'ok' })
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
    }
  },

  newGame: async (identity) => {
    set({ busy: true, error: null })
    try {
      const state = await api.newGame(identity)
      set({ state, hasSave: true, screen: 'play', busy: false })
      get().loadCharacters()
      get().loadJobs()
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

  doAction: async (action, attribute) => {
    set({ busy: true, error: null })
    try {
      // Response is {player, clock, events} (events kept separate from state).
      const { events, ...state } = await api.action({ action, attribute })
      set({ state, busy: false })
      get()._pushEvents(events)
      get().loadCharacters() // availability changes as the clock advances
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
        dialogue: { npcId, npcName: d.npc_name, tier: d.tier, node: d.node, lastGained: 0 },
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
      const res = await api.dialogueChoose(dlg.npcId, dlg.node.node_id, choiceIndex)
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
