import { useState } from 'react'
import { useGameStore } from '../state/gameStore'
import StatBar from '../components/StatBar.jsx'

const DAY_NAMES = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

// The daily action loop (Milestone 1). Placeholder world — districts and travel
// arrive in Milestone 3. For now it exercises the clock + energy systems.
export default function WorldMap() {
  const state = useGameStore((s) => s.state)
  const actions = useGameStore((s) => s.actions)
  const registry = useGameStore((s) => s.attributes)
  const doAction = useGameStore((s) => s.doAction)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  const [trainAttr, setTrainAttr] = useState('charm')

  if (!state) return null
  const { player, clock } = state

  return (
    <main className="world-map">
      <header className="hud">
        <div className="hud-clock">
          <span className="hud-time">{clock.time}</span>
          <span className="hud-date">
            Week {clock.week} · {DAY_NAMES[clock.day] ?? `Day ${clock.day}`}
          </span>
        </div>
        <div className="hud-identity">
          <strong>{player.identity.name}</strong>
          <span className="hud-sub">
            {player.identity.pronouns} · {player.species}
          </span>
        </div>
      </header>

      <StatBar />

      <section className="placeholder-world">
        <p>Nexus City stretches out around you. (Districts arrive in Milestone 3.)</p>
      </section>

      <section className="action-panel">
        <h2>What do you do?</h2>
        {error && <p className="form-error">{error}</p>}
        <div className="action-list">
          {Object.entries(actions ?? {}).map(([id, def]) =>
            def.trains ? (
              <div className="action-train" key={id}>
                <select
                  value={trainAttr}
                  onChange={(e) => setTrainAttr(e.target.value)}
                  disabled={busy}
                >
                  {Object.entries(registry ?? {}).map(([attrId, spec]) => (
                    <option key={attrId} value={attrId}>
                      {spec.name}
                    </option>
                  ))}
                </select>
                <button
                  className="btn-action"
                  disabled={busy}
                  onClick={() => doAction('train', trainAttr)}
                >
                  {def.label} ({fmtDuration(def.minutes)})
                </button>
              </div>
            ) : (
              <button
                className="btn-action"
                key={id}
                disabled={busy}
                onClick={() => doAction(id)}
              >
                {def.label} ({fmtDuration(def.minutes)})
              </button>
            ),
          )}
        </div>
      </section>
    </main>
  )
}

function fmtDuration(minutes) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h && m) return `${h}h ${m}m`
  if (h) return `${h}h`
  return `${m}m`
}
