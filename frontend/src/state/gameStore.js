import { create } from 'zustand'
import { api } from '../api/client'

// The single authoritative client-side store. Because the backend is
// server-authoritative, this store mostly mirrors state fetched from the API
// rather than owning game rules itself.
export const useGameStore = create((set) => ({
  // Connection to the backend: 'unknown' | 'ok' | 'error'
  connection: 'unknown',
  connectionError: null,
  serverInfo: null,

  checkConnection: async () => {
    try {
      const data = await api.health()
      set({ connection: 'ok', connectionError: null, serverInfo: data })
    } catch (err) {
      set({ connection: 'error', connectionError: err.message, serverInfo: null })
    }
  },
}))
