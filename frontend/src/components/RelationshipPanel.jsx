import { useGameStore } from '../state/gameStore'

// Affection per character. Renders from the characters list, which is refreshed
// whenever the clock advances or a conversation ends.
export default function RelationshipPanel() {
  const characters = useGameStore((s) => s.characters)

  if (!characters.length) return null

  return (
    <section className="relationship-panel">
      <h2>Relationships</h2>
      <ul className="relationship-list">
        {characters.map((c) => (
          <li key={c.id} className="relationship">
            <span className="relationship-name">
              {c.name} <span className="relationship-sub">{c.pronouns}</span>
            </span>
            <span className="relationship-meter">
              <span
                className="relationship-fill"
                style={{ width: `${c.affection}%` }}
              />
            </span>
            <span className="relationship-value">{c.affection}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
