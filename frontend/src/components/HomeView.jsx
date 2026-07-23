import { useState } from 'react'
import { useGameStore } from '../state/gameStore'

// A place to live. Full Rest only restores at home (a catnap is all you get out
// in the city), each home carries a perk and an item stash, and you climb from
// the ship's berth to a flavored home you rent and eventually buy.
const PERK_LABEL = {
  luck_bonus: 'Luck',
  gift_affection_bonus: 'Gift affection',
  research_topics_bonus: 'Research leads',
  train_bonus: 'Training',
  walk_minutes_mult: 'Faster walks',
  max_hp_mult: 'Vitality',
}

function perkText(perk) {
  const entries = Object.entries(perk || {})
  if (!entries.length) return null
  return entries
    .map(([k, v]) => `${PERK_LABEL[k] ?? k} ${v > 0 && v >= 1 ? `+${v}` : `×${v}`}`)
    .join(', ')
}

export default function HomeView() {
  const homes = useGameStore((s) => s.homes)
  const state = useGameStore((s) => s.state)
  const districts = useGameStore((s) => s.districts)
  const lastHomeEvent = useGameStore((s) => s.lastHomeEvent)
  const rentHome = useGameStore((s) => s.rentHome)
  const buyHome = useGameStore((s) => s.buyHome)
  const moveInHome = useGameStore((s) => s.moveInHome)
  const stashItem = useGameStore((s) => s.stashItem)
  const clearHomeNews = useGameStore((s) => s.clearHomeNews)
  const busy = useGameStore((s) => s.busy)
  const [depositId, setDepositId] = useState('')

  if (!homes) return null

  const placeName = (id) => districts?.[id]?.name ?? id
  const hoursText = (m) => `${Math.round((m / 60) * 10) / 10}h sleep`
  const current = homes.homes.find((h) => h.id === homes.current)
  const stash = state?.player?.stash ?? {}
  const inventory = state?.player?.inventory ?? {}

  return (
    <section className="home-view">
      <h2>Home</h2>

      {lastHomeEvent && (
        <div className="home-news" onClick={clearHomeNews}>
          {lastHomeEvent.evicted ? (
            <p>
              Evicted from <strong>{lastHomeEvent.home}</strong> — rent lapsed. You&apos;re back in
              the ship&apos;s berth.
            </p>
          ) : (
            <p>
              Moved into <strong>{lastHomeEvent.home}</strong>
              {lastHomeEvent.paid > 0 && ` — ${lastHomeEvent.paid} cr`}.
            </p>
          )}
        </div>
      )}

      <p className="home-current">
        You live in <strong>{homes.current_name}</strong>.{' '}
        {homes.at_home ? (
          <span className="home-athome">You can Rest here for a full night&apos;s sleep.</span>
        ) : (
          <span className="home-away">
            Go home to sleep — out here a catnap is the best you&apos;ll manage.
          </span>
        )}
      </p>

      {homes.at_home && current?.stash > 0 && (
        <div className="home-stash">
          <h3>
            Stash <span className="stash-cap">
              {Object.values(stash).reduce((a, b) => a + b, 0)}/{current.stash}
            </span>
          </h3>
          {Object.keys(stash).length > 0 ? (
            <ul className="stash-list">
              {Object.entries(stash).map(([id, qty]) => (
                <li key={id}>
                  <span>
                    {id} ×{qty}
                  </span>
                  <button
                    className="btn-action"
                    disabled={busy}
                    onClick={() => stashItem(id, 'out')}
                  >
                    Take
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="home-away">The stash is empty.</p>
          )}
          <div className="stash-deposit">
            <select value={depositId} onChange={(e) => setDepositId(e.target.value)}>
              <option value="">Stash an item…</option>
              {Object.entries(inventory).map(([id, qty]) => (
                <option key={id} value={id}>
                  {id} ×{qty}
                </option>
              ))}
            </select>
            <button
              className="btn-action"
              disabled={busy || !depositId}
              onClick={() => {
                stashItem(depositId, 'in')
                setDepositId('')
              }}
            >
              Store
            </button>
          </div>
        </div>
      )}

      <details className="home-board">
        <summary>Housing listings</summary>
        <ul className="home-list">
          {homes.homes.map((h) => {
            const perk = perkText(h.perk)
            return (
              <li
                key={h.id}
                className={`home-row home-row--t${h.tier}${h.current ? ' home-row--current' : ''}`}
              >
                <div className="home-info">
                  <span className="home-head">
                    {h.name}
                    {h.current && <span className="home-tag home-tag--current">Home</span>}
                    {!h.current && h.owned && h.id !== 'berth' && (
                      <span className="home-tag">Owned</span>
                    )}
                  </span>
                  <span className="home-place">{placeName(h.district)}</span>
                  <span className="home-vibe">{h.vibe}</span>
                  <span className="home-meta">
                    <span className="home-chip">{hoursText(h.rest_minutes)}</span>
                    {h.stash > 0 && <span className="home-chip">stash {h.stash}</span>}
                    {h.host && <span className="home-chip">hosts guests</span>}
                    {perk && <span className="home-chip home-chip--perk">{perk}</span>}
                  </span>
                </div>
                <div className="home-actions">
                  {h.rent > 0 && !h.current && (
                    <button
                      className="btn-action"
                      disabled={busy || !h.can_rent}
                      title={h.can_rent ? '' : `Needs ${h.rent} cr`}
                      onClick={() => rentHome(h.id)}
                    >
                      Rent {h.rent}/wk
                    </button>
                  )}
                  {h.price > 0 && !h.owned && (
                    <button
                      className="btn-primary"
                      disabled={busy || !h.can_buy}
                      title={h.can_buy ? '' : `Needs ${h.price} cr`}
                      onClick={() => buyHome(h.id)}
                    >
                      Buy {h.price}
                    </button>
                  )}
                  {h.owned && !h.current && (
                    <button className="btn-action" disabled={busy} onClick={() => moveInHome(h.id)}>
                      Move in
                    </button>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      </details>
    </section>
  )
}
