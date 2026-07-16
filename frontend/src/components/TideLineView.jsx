import { useGameStore } from '../state/gameStore'

// The Tide Line — salvage runs in the flooded levels, slack water only.
export default function TideLineView() {
  const state = useGameStore((s) => s.state)
  const wadeIn = useGameStore((s) => s.wadeIn)
  const lastSalvage = useGameStore((s) => s.lastSalvage)
  const busy = useGameStore((s) => s.busy)

  if (state?.player?.location !== 'the_tide_line') return null

  return (
    <section className="tideline-view">
      <h2>The Tide Line</h2>
      {lastSalvage && (
        <p className="salvage-result">
          {lastSalvage.text}
          {lastSalvage.credits != null && (
            <span className="salvage-find"> +{lastSalvage.credits} cr</span>
          )}
          {lastSalvage.item_name && (
            <span className="salvage-find"> ◈ {lastSalvage.item_name}</span>
          )}
        </p>
      )}
      <div className="salvage-offer">
        <div className="salvage-info">
          <span className="salvage-title">Wade the galleries</span>
          <span className="salvage-sub">
            Thirty cold minutes below the water line. The tide leaves things behind —
            and sometimes takes instead.
          </span>
        </div>
        <button className="btn-action" disabled={busy} onClick={wadeIn}>
          Wade in · 30m
        </button>
      </div>
    </section>
  )
}
