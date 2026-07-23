import { useGameStore } from '../state/gameStore'

// Mirrors backend world.TRAVEL_COST / CAB_COST so the UI can show costs
// before you commit. Stepping into or out of a venue within a district is
// free and instant; the Loop is the mag-tube ring; cabs fly door to door at
// a flat rate.
const COST = {
  adjacent: { walk: { minutes: 20, credits: 0 }, transit: { minutes: 8, credits: 8 } },
  cross: { walk: { minutes: 40, credits: 0 }, transit: { minutes: 18, credits: 18 } },
}
const CAB = { minutes: 6, credits: 30 }

export default function TravelPanel() {
  const districts = useGameStore((s) => s.districts)
  const venues = useGameStore((s) => s.venues)
  const homes = useGameStore((s) => s.homes)
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

  // Your home is a place you travel to, but it lives in its own registry (not
  // venues) — surface it as a dedicated destination. Only your *current* home;
  // other doors don't open. Home cost prices like any venue: a free local hop
  // when it's in this district, otherwise the district leg.
  const homeId = homes?.current
  const homeRow = homes?.homes?.find((h) => h.id === homeId)
  const homeDistrict = homeRow?.district
  const atHome = player.location === homeId
  const homeLocal = homeDistrict === hereDistrict
  const showHome = homeId && homeRow && !atHome
  const homeDist = adjacent.has(homeDistrict) ? 'adjacent' : 'cross'

  return (
    <section className="travel-panel">
      <h2>Travel</h2>
      <p className="travel-here">
        You're {insideVenue ? 'inside' : 'in'} <strong>{here?.name ?? player.location}</strong>
        {insideVenue && <span className="travel-under"> · under {districts[hereDistrict]?.name}</span>}
        {' '}· {player.credits} cr
      </p>
      {showHome && (
        <ul className="travel-list travel-list--home">
          <li className="travel-dest travel-dest--home">
            <span className="travel-name">
              🏠 {homes.current_name}
              <span className="travel-dist">
                {homeLocal ? 'go home' : homeDist === 'cross' ? 'cross-city' : 'nearby'}
              </span>
            </span>
            <span className="travel-modes">
              {homeLocal ? (
                <button className="btn-action" disabled={busy} onClick={() => travel(homeId, 'walk')}>
                  Go home
                </button>
              ) : (
                <>
                  <button
                    className="btn-action"
                    disabled={busy}
                    onClick={() => travel(homeId, 'walk')}
                  >
                    Walk · {COST[homeDist].walk.minutes}m
                  </button>
                  <button
                    className="btn-action"
                    disabled={busy || player.credits < COST[homeDist].transit.credits}
                    onClick={() => travel(homeId, 'transit')}
                  >
                    Loop · {COST[homeDist].transit.minutes}m · {COST[homeDist].transit.credits}cr
                  </button>
                  <button
                    className="btn-action travel-cab"
                    disabled={busy || player.credits < CAB.credits}
                    onClick={() => travel(homeId, 'cab')}
                  >
                    Cab · {CAB.minutes}m · {CAB.credits}cr
                  </button>
                </>
              )}
            </span>
          </li>
        </ul>
      )}
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
                  Step out
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
                  Enter
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
            const canCab = player.credits >= CAB.credits
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
                    title={canTransit ? 'Ride the Loop — the mag-tube ring' : 'Not enough credits'}
                    onClick={() => travel(d.id, 'transit')}
                  >
                    Loop · {transit.minutes}m · {transit.credits}cr
                  </button>
                  <button
                    className="btn-action travel-cab"
                    disabled={busy || !canCab}
                    title={canCab ? 'Hovercab — door to door, sky lanes' : 'Not enough credits'}
                    onClick={() => travel(d.id, 'cab')}
                  >
                    Cab · {CAB.minutes}m · {CAB.credits}cr
                  </button>
                </span>
              </li>
            )
          })}
      </ul>
    </section>
  )
}
