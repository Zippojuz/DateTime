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

  // Current game state from the server: { player, clock }
  state: null,
  hasSave: false,

  busy: false,
  error: null,

  // Load reference data + any existing save. Called once on mount.
  init: async () => {
    try {
      const [attributes, actions] = await Promise.all([
        api.attributes(),
        api.actions(),
      ])
      set({ attributes, actions, connection: 'ok' })
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
    if (get().state) set({ screen: 'play' })
  },

  newGame: async (identity) => {
    set({ busy: true, error: null })
    try {
      const state = await api.newGame(identity)
      set({ state, hasSave: true, screen: 'play', busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },

  doAction: async (action, attribute) => {
    set({ busy: true, error: null })
    try {
      const state = await api.action({ action, attribute })
      set({ state, busy: false })
    } catch (err) {
      set({ error: err.message, busy: false })
    }
  },
}))
