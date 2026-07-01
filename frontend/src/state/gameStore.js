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

  // Current game state from the server: { player, clock }
  state: null,
  hasSave: false,

  // Characters with availability + affection, refreshed as the clock moves.
  characters: [],

  // Active dialogue: null | { npcId, npcName, tier, node, lastGained }
  dialogue: null,

  busy: false,
  error: null,

  // Load reference data + any existing save. Called once on mount.
  init: async () => {
    try {
      const [attributes, actions, topics] = await Promise.all([
        api.attributes(),
        api.actions(),
        api.topics(),
      ])
      set({ attributes, actions, topics, connection: 'ok' })
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
    }
  },

  newGame: async (identity) => {
    set({ busy: true, error: null })
    try {
      const state = await api.newGame(identity)
      set({ state, hasSave: true, screen: 'play', busy: false })
      get().loadCharacters()
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

  doAction: async (action, attribute) => {
    set({ busy: true, error: null })
    try {
      const state = await api.action({ action, attribute })
      set({ state, busy: false })
      get().loadCharacters() // availability changes as the clock advances
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

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
