import { useGameStore } from '../state/gameStore'
import PreferenceTags from './PreferenceTags.jsx'

// Affection is signed (−100…+100, 0 = neutral). The meter fills from the centre:
// left of centre = negative, right = positive.
function affectionLabel(value) {
  if (value <= -60) return 'Hostile'
  if (value < -15) return 'Cold'
  if (value <= 15) return 'Neutral'
  if (value < 60) return 'Warm'
  return 'Close'
}

export default function RelationshipPanel() {
  const characters = useGameStore((s) => s.characters)

  if (!characters.length) return null

  return (
    <section className="relationship-panel">
      <h2>Relationships</h2>
      <ul className="relationship-list">
        {characters.map((c) => {
          const pct = (c.affection + 100) / 2 // −100..100 → 0..100
          const positive = c.affection >= 0
          return (
            <li key={c.id} className="relationship">
              <div className="relationship-head">
                <span className="relationship-name">
                  {c.name} <span className="relationship-sub">{c.pronouns}</span>
                </span>
                <span className="relationship-mood">
                  {affectionLabel(c.affection)} ({c.affection})
                </span>
              </div>
              <div className="relationship-meter">
                <span className="relationship-centre" />
                <span
                  className={`relationship-fill ${positive ? 'is-pos' : 'is-neg'}`}
                  style={{ width: `${Math.abs(c.affection) / 2}%`, left: positive ? '50%' : `${pct}%` }}
                />
              </div>
              <div className="relationship-prefs">
                What you know: <PreferenceTags preferences={c.preferences} />
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
