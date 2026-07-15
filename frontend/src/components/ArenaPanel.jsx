import { useGameStore } from '../state/gameStore'

// The Pit — the unlicensed arena under the docks. A pure win ladder: no XP,
// no loot, every 10th win a championship. The Pit pays in reputation.
export default function ArenaPanel() {
  const player = useGameStore((s) => s.state?.player)
  const arena = useGameStore((s) => s.arena)
  const dungeon = useGameStore((s) => s.dungeon)
  const arenaFight = useGameStore((s) => s.arenaFight)
  const busy = useGameStore((s) => s.busy)

  if (!player || !arena || player.location !== arena.district) return null

  const next = arena.next
  const inRun = Boolean(dungeon?.run)
  const inFight = Boolean(dungeon?.combat)
  const tooTired = player.energy < arena.energy

  return (
    <section className="arena-panel">
      <h2>{arena.name}</h2>
      <p className="arena-blurb">{arena.blurb}</p>
      <p className="arena-record">
        Record <strong>{arena.wins}</strong> wins · <strong>{arena.titles}</strong> titles ·{' '}
        cred <strong>{arena.street_cred}</strong>{' '}
        <span className="arena-stage">({arena.cred_stage})</span>
      </p>

      <div className={`arena-card${next.championship ? ' arena-card--championship' : ''}`}>
        {next.championship && <span className="arena-champ-tag">CHAMPIONSHIP · {next.title}</span>}
        <p className="arena-next">
          Fight #{next.number}: <strong>{next.enemy.name}</strong>{' '}
          <span className={`element element--${next.enemy.element}`}>{next.enemy.element}</span>
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
          Step into the Pit
        </button>
      </div>
    </section>
  )
}
