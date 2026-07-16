import { useGameStore } from '../state/gameStore'

// The Steeps' front desk: the paid soak (fast, expensive sleep).
export default function SteepsView() {
  const state = useGameStore((s) => s.state)
  const venues = useGameStore((s) => s.venues)
  const takeSoak = useGameStore((s) => s.takeSoak)
  const lastSoak = useGameStore((s) => s.lastSoak)
  const busy = useGameStore((s) => s.busy)

  if (state?.player?.location !== 'the_steeps') return null
  const soak = venues?.the_steeps?.soak
  if (!soak) return null

  return (
    <section className="steeps-view">
      <h2>The Steeps</h2>
      {lastSoak && <p className="soak-line">{lastSoak.line}</p>}
      <div className="soak-offer">
        <div className="soak-info">
          <span className="soak-title">Take the waters</span>
          <span className="soak-sub">{soak.blurb}</span>
        </div>
        <button className="btn-action" disabled={busy} onClick={takeSoak}>
          Soak · 1h 30m · {soak.cost}cr
        </button>
      </div>
    </section>
  )
}
