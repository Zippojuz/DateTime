import { useGameStore } from '../state/gameStore'

// The way down into the Substrate — only visible in The Shallows.
export default function SubstratePanel() {
  const player = useGameStore((s) => s.state?.player)
  const dungeon = useGameStore((s) => s.dungeon)
  const difficulties = useGameStore((s) => s.difficulties)
  const party = useGameStore((s) => s.party)
  const enterDungeon = useGameStore((s) => s.enterDungeon)
  const setDifficulty = useGameStore((s) => s.setDifficulty)
  const recruitCompanion = useGameStore((s) => s.recruitCompanion)
  const dismissCompanion = useGameStore((s) => s.dismissCompanion)
  const busy = useGameStore((s) => s.busy)

  if (!player || player.location !== 'the_shallows') return null

  const inRun = Boolean(dungeon?.run)

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
          disabled={busy || player.energy < 10 || inRun}
          title={player.energy < 10 ? 'Too tired (needs 10 energy)' : ''}
          onClick={enterDungeon}
        >
          Descend
        </button>
      </div>

      {party && (
        <div className="party-panel">
          <h3>Delving partner</h3>
          <p className="party-hint">
            One companion follows you down. Friendship ({party.required_affection}+ affection)
            earns their trust — and delving together deepens it.
          </p>
          <ul className="party-list">
            {party.candidates.map((c) => {
              const isCurrent = party.companion === c.id
              return (
                <li key={c.id} className={`party-row${isCurrent ? ' party-row--current' : ''}`}>
                  <div className="party-info">
                    <strong>{c.name}</strong>{' '}
                    <span className="party-role">
                      {c.role} · {c.element}
                    </span>
                    <p className="party-blurb">{c.blurb}</p>
                  </div>
                  {isCurrent ? (
                    <button
                      className="btn-action"
                      disabled={busy || inRun}
                      onClick={dismissCompanion}
                    >
                      Dismiss
                    </button>
                  ) : (
                    <button
                      className="btn-action"
                      disabled={busy || inRun || !c.recruitable}
                      title={
                        c.recruitable
                          ? ''
                          : `Needs ${party.required_affection}+ affection (now ${c.affection})`
                      }
                      onClick={() => recruitCompanion(c.id)}
                    >
                      Recruit
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </section>
  )
}
