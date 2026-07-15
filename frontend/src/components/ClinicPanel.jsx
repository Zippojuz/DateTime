import { useState } from 'react'
import { useGameStore } from '../state/gameStore'

const ASPECTS = [
  { id: 'appearance', label: 'Appearance', threshold: 15 },
  { id: 'pronouns', label: 'Pronouns', threshold: 25 },
  { id: 'body', label: 'Body', threshold: 40 },
]

// Second Skin, Juno's clinic in The Grid — the home of the transformation
// system. Aspects unlock as Juno comes to trust you; what you change is
// entirely yours. (Identity is data here, never a gate.)
export default function ClinicPanel() {
  const player = useGameStore((s) => s.state?.player)
  const transform = useGameStore((s) => s.transform)
  const busy = useGameStore((s) => s.busy)
  const [drafts, setDrafts] = useState({})

  if (!player || player.location !== 'the_grid') return null

  const unlocked = player.unlocked_transformations ?? []

  const commit = (aspect) => {
    const value = (drafts[aspect] ?? '').trim()
    if (!value) return
    transform({ [aspect]: value })
    setDrafts((d) => ({ ...d, [aspect]: '' }))
  }

  return (
    <section className="clinic-panel">
      <h2>Second Skin</h2>
      <p className="clinic-blurb">
        Juno&apos;s clinic. Soft light, sleeping chrome, very forgiving paperwork.
        &quot;Tell me what your body&apos;s getting wrong about you lately.&quot;
      </p>
      <ul className="clinic-list">
        {ASPECTS.map(({ id, label }) => (
          <li key={id} className="clinic-aspect">
            <span className="clinic-aspect-name">{label}</span>
            {unlocked.includes(id) ? (
              <span className="clinic-edit">
                <span className="clinic-current">{player.identity[id] || '—'}</span>
                <input
                  type="text"
                  value={drafts[id] ?? ''}
                  placeholder={`New ${label.toLowerCase()}…`}
                  onChange={(e) => setDrafts((d) => ({ ...d, [id]: e.target.value }))}
                />
                <button
                  className="btn-action"
                  disabled={busy || !(drafts[id] ?? '').trim()}
                  onClick={() => commit(id)}
                >
                  Change
                </button>
              </span>
            ) : (
              <span className="clinic-locked">
                Juno will offer this once she trusts you more.
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
