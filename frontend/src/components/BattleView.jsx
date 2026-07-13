import { useGameStore } from '../state/gameStore'

const STATUS_HINT = {
  burn: 'taking damage each turn',
  slow: 'no charge regen',
  charm: 'your damage halved',
  corrode: 'defense halved',
}

function StatusChips({ effects }) {
  const entries = Object.entries(effects ?? {})
  if (!entries.length) return null
  return (
    <span className="status-chips">
      {entries.map(([name, e]) => (
        <span key={name} className={`status status--${name}`} title={STATUS_HINT[name]}>
          {name} {e.turns}
        </span>
      ))}
    </span>
  )
}

// Turn-based battle UI: enemy card, HP bars, action buttons, combat log.
export default function BattleView() {
  const dungeon = useGameStore((s) => s.dungeon)
  const items = useGameStore((s) => s.items)
  const inventory = useGameStore((s) => s.state?.player?.inventory ?? {})
  const act = useGameStore((s) => s.combatAct)
  const busy = useGameStore((s) => s.busy)

  const combat = dungeon?.combat
  const stats = dungeon?.stats
  const skills = dungeon?.skills ?? {}
  if (!combat) return null

  const enemy = combat.enemy
  const usable = Object.entries(inventory).filter(([id]) =>
    ['food', 'booster'].includes(items?.[id]?.type),
  )
  const isBoss = enemy.role === 'boss'

  return (
    <section className="battle">
      <div className={`battle-enemy ${enemy.role !== 'normal' ? 'battle-enemy--boss' : ''}`}>
        <div className="battle-enemy-head">
          <strong>{enemy.name}</strong>
          <span className={`element element--${enemy.element}`}>{enemy.element}</span>
          {enemy.role !== 'normal' && <span className="battle-role">{enemy.role}</span>}
        </div>
        <p className="battle-desc">{enemy.description}</p>
        <HpBar label="" value={combat.enemy_hp} max={enemy.hp} kind="enemy" />
        <StatusChips effects={combat.enemy_effects} />
      </div>

      {combat.charging && (
        <div className="battle-telegraph" role="alert">
          ⚠ {combat.charging.telegraph}
        </div>
      )}

      <div className="battle-log">
        {combat.log.slice(-4).map((line, i) => (
          <p key={i}>{line}</p>
        ))}
      </div>

      <div className="battle-you">
        <HpBar label="You" value={combat.player_hp} max={stats.max_hp} kind="you" />
        <StatusChips effects={combat.player_effects} />
        <span className="battle-charge" title="Charge powers skills">
          Charge: {'●'.repeat(combat.charge)}{'○'.repeat(Math.max(0, 5 - combat.charge))}
        </span>
      </div>

      <div className="battle-actions">
        <button className="btn-action" disabled={busy} onClick={() => act('attack')}>
          Attack
        </button>
        {Object.values(skills).map((s) => (
          <button
            key={s.id}
            className="btn-action"
            disabled={busy || combat.charge < s.cost}
            title={`${s.description} (${s.element}, ${s.cost} charge)`}
            onClick={() => act('skill', { skill_id: s.id })}
          >
            {s.name} <span className={`element element--${s.element}`}>{s.cost}●</span>
          </button>
        ))}
        <button className="btn-action" disabled={busy} onClick={() => act('guard')}>
          Guard
        </button>
        {usable.map(([id, qty]) => (
          <button
            key={id}
            className="btn-action"
            disabled={busy}
            title={items[id].description}
            onClick={() => act('item', { item_id: id })}
          >
            {items[id].name} ×{qty}
          </button>
        ))}
        <button
          className="btn-action"
          disabled={busy || isBoss}
          title={isBoss ? "Bosses won't let you leave" : ''}
          onClick={() => act('flee')}
        >
          Flee
        </button>
      </div>
    </section>
  )
}

function HpBar({ label, value, max, kind }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className="hpbar">
      {label && <span className="hpbar-label">{label}</span>}
      <div className="hpbar-track">
        <span className={`hpbar-fill hpbar-fill--${kind}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="hpbar-num">
        {value}/{max}
      </span>
    </div>
  )
}
