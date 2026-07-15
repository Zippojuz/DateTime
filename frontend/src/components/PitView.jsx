import { useGameStore } from '../state/gameStore'

// The Pit — a real venue under the Grid. Fight card, the book (leaderboard),
// the belt rack, and Ondo at ringside. Renders only while you're inside.
export default function PitView() {
  const player = useGameStore((s) => s.state?.player)
  const arena = useGameStore((s) => s.arena)
  const venues = useGameStore((s) => s.venues)
  const dungeon = useGameStore((s) => s.dungeon)
  const arenaFight = useGameStore((s) => s.arenaFight)
  const busy = useGameStore((s) => s.busy)

  if (!player || !arena || player.location !== arena.venue) return null

  const venue = venues?.[arena.venue]
  const next = arena.next
  const inRun = Boolean(dungeon?.run)
  const inFight = Boolean(dungeon?.combat)
  const tooTired = player.energy < arena.energy

  return (
    <section className="pit-view">
      <header className="pit-head">
        <h2>{arena.name}</h2>
        {venue?.hours && (
          <span className="pit-hours">
            first bell {venue.hours.open} · last {venue.hours.close}
          </span>
        )}
      </header>
      <p className="arena-blurb">{venue?.vibe ?? arena.blurb}</p>

      {arena.open === false ? (
        <p className="pit-closed">{arena.closed_line}</p>
      ) : (
        <>
          <p className="pit-bell-line">{arena.bell_line}</p>
          <p className="arena-record">
            Record <strong>{arena.wins}</strong> wins · <strong>{arena.titles}</strong> titles ·{' '}
            cred <strong>{arena.street_cred}</strong>{' '}
            <span className="arena-stage">({arena.cred_stage})</span>
          </p>

          <div className={`arena-card${next.championship ? ' arena-card--championship' : ''}`}>
            {next.championship && (
              <span className="arena-champ-tag">CHAMPIONSHIP · {next.title}</span>
            )}
            <p className="arena-next">
              Fight #{next.number}: <strong>{next.enemy.name}</strong>{' '}
              <span className={`element element--${next.enemy.element}`}>
                {next.enemy.element}
              </span>
            </p>
            <button
              className="btn-primary"
              disabled={busy || inRun || inFight || tooTired}
              title={
                inRun
                  ? "The Pit doesn't book fighters mid-delve"
                  : tooTired
                    ? `Too tired (needs ${arena.energy} energy)`
                    : ''
              }
              onClick={arenaFight}
            >
              Step into the ring
            </button>
          </div>
        </>
      )}

      <div className="pit-belts">
        <h3>The Belt Rack</h3>
        <ul>
          {arena.belts.map((belt) => (
            <li
              key={belt.number}
              className={`pit-belt${belt.claimed ? ' pit-belt--claimed' : ''}`}
            >
              <span className="pit-belt-title">{belt.title}</span>
              <span className="pit-belt-holder">
                {belt.claimed ? 'YOURS' : belt.holder}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="pit-book">
        <h3>The Book</h3>
        <div className="pit-founder">
          <span className="pit-rank">—</span>
          <span className="pit-name">{arena.founder.name}</span>
          <span className="pit-wins">{arena.founder.record}</span>
        </div>
        <ol className="pit-board">
          {arena.leaderboard.map((row) => (
            <li key={row.name} className={row.you ? 'pit-row pit-row--you' : 'pit-row'}>
              <span className="pit-rank">{row.rank}</span>
              <span className="pit-name">{row.name}</span>
              <span className="pit-wins">{row.wins}W</span>
              <span className="pit-note">{row.note}</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
