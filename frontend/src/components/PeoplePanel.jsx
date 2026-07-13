import { useGameStore } from '../state/gameStore'

// Availability labels per arrival tier (the design doc's "Arriving Late").
const TIER_LABEL = {
  full: 'Available',
  shortened: 'Winding down',
  brief: 'About to leave',
  missed: 'Just missed them',
  unavailable: 'Not around',
}

// Who you can reach right now. You must be in the same district as an NPC to
// talk to them; otherwise the panel tells you where to go.
export default function PeoplePanel() {
  const characters = useGameStore((s) => s.characters)
  const districts = useGameStore((s) => s.districts)
  const startDialogue = useGameStore((s) => s.startDialogue)
  const startGift = useGameStore((s) => s.startGift)
  const busy = useGameStore((s) => s.busy)

  if (!characters.length) return null

  const districtName = (id) => districts?.[id]?.name ?? id

  return (
    <section className="people-panel">
      <h2>People</h2>
      <ul className="people-list">
        {characters.map((c) => {
          const av = c.availability
          const canTalk = c.reachable && !c.talked_today
          let status
          if (c.talked_today && c.reachable) status = 'already talked today'
          else if (c.reachable) status = TIER_LABEL[av.tier]
          else if (av.available && av.district) status = `in ${districtName(av.district)}`
          else status = `${TIER_LABEL[av.tier] ?? 'Not around'} · ${districtName(c.district)}`

          return (
            <li key={c.id} className="person">
              <div className="person-info">
                <strong>{c.name}</strong>
                <span className="person-sub">{status}</span>
              </div>
              <div className="person-actions">
                <button
                  className="btn-action"
                  disabled={!canTalk || busy}
                  onClick={() => startDialogue(c.id)}
                >
                  Talk
                </button>
                <button
                  className="btn-action"
                  disabled={!c.reachable || busy}
                  onClick={() => startGift(c.id, c.name)}
                >
                  Gift
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
