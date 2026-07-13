import { useGameStore } from '../state/gameStore'

// The way down into the Substrate — only visible in The Shallows.
export default function SubstratePanel() {
  const player = useGameStore((s) => s.state?.player)
  const dungeon = useGameStore((s) => s.dungeon)
  const difficulties = useGameStore((s) => s.difficulties)
  const enterDungeon = useGameStore((s) => s.enterDungeon)
  const setDifficulty = useGameStore((s) => s.setDifficulty)
  const busy = useGameStore((s) => s.busy)

  if (!player || player.location !== 'the_shallows') return null

  return (
    <section className="substrate-panel">
      <h2>The Substrate</h2>
      <p className="substrate-blurb">
        A maintenance shaft yawns behind the market — the way down into the old
        structure beneath the city. Locals don't talk about it. Lv{' '}
        {player.combat_level} · deepest floor: {player.max_floor || '—'}
      </p>
      <div className="substrate-controls">
        <select
          value={player.difficulty}
          disabled={busy}
          onChange={(e) => setDifficulty(e.target.value)}
          title={difficulties?.[player.difficulty]?.description}
        >
          {Object.entries(difficulties ?? {}).map(([id, d]) => (
            <option key={id} value={id}>
              {d.name}
            </option>
          ))}
        </select>
        <button
          className="btn-primary"
          disabled={busy || player.energy < 10 || dungeon?.run}
          title={player.energy < 10 ? 'Too tired (needs 10 energy)' : ''}
          onClick={enterDungeon}
        >
          Descend
        </button>
      </div>
    </section>
  )
}
