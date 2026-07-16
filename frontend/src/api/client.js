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
  venues: () => request('/venues'),
  species: () => request('/species'),
  protocols: () => request('/protocols'),
  statuses: () => request('/statuses'),
  travel: (to, mode) =>
    request('/travel', { method: 'POST', body: JSON.stringify({ to, mode }) }),
  jobs: () => request('/jobs'),
  work: (jobId) =>
    request('/job', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),
  gigs: () => request('/gigs'),
  workGig: (gigId, choiceIndex) =>
    request('/gig', {
      method: 'POST',
      body: JSON.stringify({ gig_id: gigId, choice_index: choiceIndex }),
    }),
  payDebt: (amount) =>
    request('/debt/pay', { method: 'POST', body: JSON.stringify({ amount }) }),
  items: () => request('/items'),
  shop: () => request('/shop'),
  buy: (itemId) =>
    request('/shop/buy', { method: 'POST', body: JSON.stringify({ item_id: itemId }) }),
  marketGossip: () => request('/market/gossip', { method: 'POST', body: '{}' }),
  useItem: (itemId) =>
    request('/item/use', { method: 'POST', body: JSON.stringify({ item_id: itemId }) }),
  gift: (npcId, itemId) =>
    request('/gift', { method: 'POST', body: JSON.stringify({ npc_id: npcId, item_id: itemId }) }),
  dungeonState: () => request('/dungeon/state'),
  dungeonEnter: () => request('/dungeon/enter', { method: 'POST', body: '{}' }),
  dungeonMove: (dir) =>
    request('/dungeon/move', { method: 'POST', body: JSON.stringify({ dir }) }),
  dungeonSearch: () => request('/dungeon/search', { method: 'POST', body: '{}' }),
  dungeonInteract: () => request('/dungeon/interact', { method: 'POST', body: '{}' }),
  dungeonEvent: (choiceIndex) =>
    request('/dungeon/event', {
      method: 'POST',
      body: JSON.stringify({ choice_index: choiceIndex }),
    }),
  dungeonCurio: (curioId, verb) =>
    request('/dungeon/curio', {
      method: 'POST',
      body: JSON.stringify({ curio_id: curioId, verb }),
    }),
  dungeonProtocol: (protocolId) =>
    request('/dungeon/protocol', {
      method: 'POST',
      body: JSON.stringify({ protocol_id: protocolId }),
    }),
  dungeonLeave: () => request('/dungeon/leave', { method: 'POST', body: '{}' }),
  arena: () => request('/arena'),
  arenaFight: () => request('/arena/fight', { method: 'POST', body: '{}' }),
  party: () => request('/party'),
  recruit: (npcId) =>
    request('/party/recruit', { method: 'POST', body: JSON.stringify({ npc_id: npcId }) }),
  dismissCompanion: () => request('/party/dismiss', { method: 'POST', body: '{}' }),
  combatAction: (payload) =>
    request('/combat/action', { method: 'POST', body: JSON.stringify(payload) }),
  equipment: () => request('/equipment'),
  equip: (itemId, slot) =>
    request('/equipment/equip', {
      method: 'POST',
      body: JSON.stringify({ item_id: itemId, slot }),
    }),
  unequip: (slot) =>
    request('/equipment/unequip', { method: 'POST', body: JSON.stringify({ slot }) }),
  socketGem: (slot, gemId, index) =>
    request('/equipment/socket', {
      method: 'POST',
      body: JSON.stringify({ slot, gem_id: gemId, index }),
    }),
  unsocketGem: (slot, index) =>
    request('/equipment/unsocket', {
      method: 'POST',
      body: JSON.stringify({ slot, index }),
    }),
  difficulties: () => request('/difficulty'),
  setDifficulty: (level) =>
    request('/difficulty', { method: 'POST', body: JSON.stringify({ level }) }),
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
  dialogueChoose: (npcId, dialogueId, nodeId, choiceIndex) =>
    request('/dialogue/choose', {
      method: 'POST',
      body: JSON.stringify({
        npc_id: npcId,
        dialogue_id: dialogueId,
        node_id: nodeId,
        choice_index: choiceIndex,
      }),
    }),
}
