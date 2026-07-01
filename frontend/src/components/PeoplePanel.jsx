import { useGameStore } from '../state/gameStore'

// Availability labels per arrival tier (the design doc's "Arriving Late").
const TIER_LABEL = {
  full: 'Available',
  shortened: 'Winding down',
  brief: 'About to leave',
  missed: 'Just missed them',
  unavailable: 'Not around',
}

// Schedule-based "who can I talk to right now" list. Real district travel and
// the map arrive in Milestone 3.
export default function PeoplePanel() {
  const characters = useGameStore((s) => s.characters)
  const startDialogue = useGameStore((s) => s.startDialogue)
  const busy = useGameStore((s) => s.busy)

  if (!characters.length) return null

  return (
    <section className="people-panel">
      <h2>People</h2>
      <ul className="people-list">
        {characters.map((c) => {
          const av = c.availability
          const canTalk = av.available && !c.talked_today
          return (
            <li key={c.id} className="person">
              <div className="person-info">
                <strong>{c.name}</strong>
                <span className="person-sub">
                  {TIER_LABEL[av.tier] ?? 'Not around'}
                  {c.talked_today && av.available ? ' · already talked today' : ''}
                </span>
              </div>
              <button
                className="btn-action"
                disabled={!canTalk || busy}
                onClick={() => startDialogue(c.id)}
              >
                Talk
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
