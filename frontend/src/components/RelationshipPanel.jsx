import { useGameStore } from '../state/gameStore'
import PreferenceTags from './PreferenceTags.jsx'

// Your bonds ledger — lives on the Cyberlink now. Affection is signed
// (−100…+100, 0 = neutral); the meter fills from the centre. Only people
// you've actually met in person appear here (the link needs a handshake).
export default function RelationshipPanel() {
  const characters = useGameStore((s) => s.characters)

  const met = characters.filter((c) => c.met)

  if (!met.length) {
    return (
      <p className="link-empty">
        You haven&apos;t met anyone yet. Bonds show up here once you&apos;ve talked to someone in
        person.
      </p>
    )
  }

  return (
    <section className="relationship-panel">
      <ul className="relationship-list">
        {met.map((c) => {
          const pct = (c.affection + 100) / 2 // −100..100 → 0..100
          const positive = c.affection >= 0
          return (
            <li key={c.id} className="relationship">
              <div className="relationship-head">
                <span className="relationship-name">
                  {c.name} <span className="relationship-sub">{c.pronouns}</span>
                </span>
                <span className="relationship-mood">
                  {c.stage} ({c.affection})
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
