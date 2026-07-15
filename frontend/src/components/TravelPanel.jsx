import { useGameStore } from '../state/gameStore'

// Mirrors backend world.TRAVEL_COST / LOCAL_COST so the UI can show costs
// before you commit. "local" is a hop within one district: stepping into or
// out of a venue like the Pit.
const COST = {
  adjacent: { walk: { minutes: 20, credits: 0 }, transit: { minutes: 8, credits: 8 } },
  cross: { walk: { minutes: 40, credits: 0 }, transit: { minutes: 18, credits: 18 } },
}
const LOCAL = { minutes: 5, credits: 0 }

export default function TravelPanel() {
  const districts = useGameStore((s) => s.districts)
  const venues = useGameStore((s) => s.venues)
  const player = useGameStore((s) => s.state?.player)
  const travel = useGameStore((s) => s.travel)
  const busy = useGameStore((s) => s.busy)

  if (!districts || !player) return null

  const insideVenue = venues?.[player.location]
  const here = districts[player.location] ?? insideVenue
  const hereDistrict = insideVenue ? insideVenue.district : player.location
  const adjacent = new Set(districts[hereDistrict]?.adjacent ?? [])
  const localVenues = Object.values(venues ?? {}).filter(
    (v) => v.district === hereDistrict && v.id !== player.location,
  )

  return (
    <section className="travel-panel">
      <h2>Travel</h2>
      <p className="travel-here">
        You're {insideVenue ? 'inside' : 'in'} <strong>{here?.name ?? player.location}</strong>
        {insideVenue && <span className="travel-under"> · under {districts[hereDistrict]?.name}</span>}
        {' '}· {player.credits} cr
      </p>
      {(localVenues.length > 0 || insideVenue) && (
        <ul className="travel-list travel-list--local">
          {insideVenue && (
            <li className="travel-dest travel-dest--venue">
              <span className="travel-name">
                {districts[hereDistrict]?.name}
                <span className="travel-dist">step out</span>
              </span>
              <span className="travel-modes">
                <button
                  className="btn-action"
                  disabled={busy}
                  onClick={() => travel(hereDistrict, 'walk')}
                >
                  Climb up · {LOCAL.minutes}m
                </button>
              </span>
            </li>
          )}
          {localVenues.map((v) => (
            <li key={v.id} className="travel-dest travel-dest--venue">
              <span className="travel-name">
                {v.name}
                <span className="travel-dist">
                  here{v.hours ? ` · ${v.hours.open}–${v.hours.close}` : ''}
                </span>
              </span>
              <span className="travel-modes">
                <button
                  className="btn-action"
                  disabled={busy}
                  onClick={() => travel(v.id, 'walk')}
                >
                  Enter · {LOCAL.minutes}m
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
      <ul className="travel-list">
        {Object.values(districts)
          .filter((d) => d.id !== hereDistrict)
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
