import { useGameStore } from '../state/gameStore'

// Mirrors backend world.TRAVEL_COST so the UI can show costs before you commit.
const COST = {
  adjacent: { walk: { minutes: 20, credits: 0 }, transit: { minutes: 8, credits: 8 } },
  cross: { walk: { minutes: 40, credits: 0 }, transit: { minutes: 18, credits: 18 } },
}

export default function TravelPanel() {
  const districts = useGameStore((s) => s.districts)
  const player = useGameStore((s) => s.state?.player)
  const travel = useGameStore((s) => s.travel)
  const busy = useGameStore((s) => s.busy)

  if (!districts || !player) return null

  const here = districts[player.location]
  const adjacent = new Set(here?.adjacent ?? [])

  return (
    <section className="travel-panel">
      <h2>Travel</h2>
      <p className="travel-here">
        You're in <strong>{here?.name ?? player.location}</strong> · {player.credits} cr
      </p>
      <ul className="travel-list">
        {Object.values(districts)
          .filter((d) => d.id !== player.location)
          .map((d) => {
            const dist = adjacent.has(d.id) ? 'adjacent' : 'cross'
            const walk = COST[dist].walk
            const transit = COST[dist].transit
            const canTransit = player.credits >= transit.credits
            return (
              <li key={d.id} className="travel-dest">
                <span className="travel-name">
                  {d.name}
                  <span className="travel-dist">{dist === 'cross' ? 'cross-city' : 'nearby'}</span>
                </span>
                <span className="travel-modes">
                  <button
                    className="btn-action"
                    disabled={busy}
                    onClick={() => travel(d.id, 'walk')}
                  >
                    Walk · {walk.minutes}m
                  </button>
                  <button
                    className="btn-action"
                    disabled={busy || !canTransit}
                    title={canTransit ? '' : 'Not enough credits'}
                    onClick={() => travel(d.id, 'transit')}
                  >
                    Transit · {transit.minutes}m · {transit.credits}cr
                  </button>
                </span>
              </li>
            )
          })}
      </ul>
    </section>
  )
}
