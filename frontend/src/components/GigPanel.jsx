import { useGameStore } from '../state/gameStore'

// Mama Vex's daily gig — gray-market work out of the Docking Quarter back
// room. One a day; the dirty option pays better and costs something else.
export default function GigPanel() {
  const player = useGameStore((s) => s.state?.player)
  const gigs = useGameStore((s) => s.gigs)
  const lastGig = useGameStore((s) => s.lastGig)
  const workGig = useGameStore((s) => s.workGig)
  const busy = useGameStore((s) => s.busy)

  if (!player || player.location !== 'docking_quarter' || !gigs) return null

  const { gig, done_today: done, reachable } = gigs

  return (
    <section className="gig-panel">
      <h2>Vex&apos;s Board</h2>
      {lastGig && (
        <p className="gig-result">
          {lastGig.text} <span className="gig-pay">+{lastGig.pay} cr</span>
          {lastGig.cred_gained > 0 && (
            <span className="gig-cred"> · +{lastGig.cred_gained} cred</span>
          )}
        </p>
      )}
      {done ? (
        <p className="gig-note">One gig a day. &quot;Pace yourself, line item.&quot;</p>
      ) : !reachable ? (
        <p className="gig-note">
          Vex isn&apos;t holding court right now — the back room opens at noon.
        </p>
      ) : (
        <>
          <h3 className="gig-name">{gig.name}</h3>
          <p className="gig-brief">{gig.brief}</p>
          <div className="gig-choices">
            {gig.choices.map((c, i) => (
              <button
                key={i}
                className={`dialogue-choice${i === 1 ? ' gig-choice--dirty' : ''}`}
                disabled={busy}
                onClick={() => workGig(gig.id, i)}
              >
                {c.text} <span className="gig-pay">+{c.pay} cr</span>
                {c.cred > 0 && <span className="gig-cred"> · +{c.cred} cred</span>}
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
