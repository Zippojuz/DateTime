import { useGameStore } from '../state/gameStore'

// Availability labels per arrival tier (the design doc's "Arriving Late").
const TIER_LABEL = {
  full: 'Available',
  shortened: 'Winding down',
  brief: 'About to leave',
  missed: 'Just missed them',
  unavailable: 'Not around',
}

// Who you can reach right now. You must be in the same place as an NPC to
// talk to them; otherwise the panel tells you where to go — or where they've
// gone in the off hours (everyone lives somewhere).
export default function PeoplePanel() {
  const characters = useGameStore((s) => s.characters)
  const districts = useGameStore((s) => s.districts)
  const venues = useGameStore((s) => s.venues)
  const startDialogue = useGameStore((s) => s.startDialogue)
  const startGift = useGameStore((s) => s.startGift)
  const openAskOut = useGameStore((s) => s.openAskOut)
  const busy = useGameStore((s) => s.busy)

  if (!characters.length) return null

  const placeName = (id) => districts?.[id]?.name ?? venues?.[id]?.name ?? id

  // Only the people actually in this area — not the whole city's roster.
  const here = characters.filter((c) => c.here)

  return (
    <section className="people-panel">
      <h2>People</h2>
      {here.length === 0 && <p className="people-empty">No one's around here right now.</p>}
      <ul className="people-list">
        {here.map((c) => {
          const av = c.availability
          const canTalk = c.reachable && !c.talked_today
          let status
          if (c.talked_today && c.reachable) status = 'already talked today'
          else if (c.reachable) status = TIER_LABEL[av.tier]
          else if (av.available && av.district) status = `in ${placeName(av.district)}`
          else {
            const home = av.location === 'home' && c.home?.name
            const where = home || placeName(av.district ?? c.district)
            status = `${av.activity ?? TIER_LABEL[av.tier] ?? 'Not around'} · ${where}`
          }

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
                <button
                  className="btn-action"
                  disabled={!c.reachable || c.dated_this_week || busy}
                  title={c.dated_this_week ? 'One outing a week — keep it rare' : 'Ask them out'}
                  onClick={() => openAskOut(c.id, c.name)}
                >
                  Ask out
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
