// Thin fetch wrapper around the Flask API. In dev, Vite proxies /api to the
// backend (see vite.config.js), so a relative base works out of the box.
const BASE = import.meta.env.VITE_API_BASE ?? ''

async function request(path, options = {}) {
  const res = await fetch(`${BASE}/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    const err = new Error(data.error || `Request failed (${res.status})`)
    err.status = res.status
    throw err
  }

  return data
}

export const api = {
  health: () => request('/health'),
  attributes: () => request('/attributes'),
  actions: () => request('/actions'),
  topics: () => request('/topics'),
  districts: () => request('/districts'),
  travel: (to, mode) =>
    request('/travel', { method: 'POST', body: JSON.stringify({ to, mode }) }),
  jobs: () => request('/jobs'),
  work: (jobId) =>
    request('/job', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),
  payDebt: (amount) =>
    request('/debt/pay', { method: 'POST', body: JSON.stringify({ amount }) }),
  getState: () => request('/game/state'),
  newGame: (identity) =>
    request('/game/new', { method: 'POST', body: JSON.stringify(identity) }),
  action: (payload) =>
    request('/action', { method: 'POST', body: JSON.stringify(payload) }),
  transform: (changes) =>
    request('/player/transform', {
      method: 'POST',
      body: JSON.stringify({ changes }),
    }),
  characters: () => request('/characters'),
  dialogueStart: (npcId) =>
    request('/dialogue/start', { method: 'POST', body: JSON.stringify({ npc_id: npcId }) }),
  dialogueChoose: (npcId, nodeId, choiceIndex) =>
    request('/dialogue/choose', {
      method: 'POST',
      body: JSON.stringify({ npc_id: npcId, node_id: nodeId, choice_index: choiceIndex }),
    }),
}
