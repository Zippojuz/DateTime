import { useState } from 'react'
import { useGameStore } from '../state/gameStore'

const STATUS_HINT = {
  burn: 'taking damage each turn',
  slow: 'no charge regen',
  charm: 'your damage halved',
  corrode: 'defense halved',
}

const ROLE_ICON = {
  tank: '⛨',
  healer: '✚',
  dps: '⚔',
  support: '♪',
  rogue: '☄',
}

const ENEMY_ICON = { normal: '⚔', miniboss: '☠', boss: '♛' }

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

// FF7-style battle popup: a wide modal window — party on the left of the
// battlefield, enemy on the right, message box up top, command menu and
// party status strip along the bottom.
export default function BattleView() {
  const dungeon = useGameStore((s) => s.dungeon)
  const items = useGameStore((s) => s.items)
  const player = useGameStore((s) => s.state?.player)
  const inventory = player?.inventory ?? {}
  const act = useGameStore((s) => s.combatAct)
  const busy = useGameStore((s) => s.busy)
  const [menu, setMenu] = useState(null) // null | 'skills' | 'items'

  const combat = dungeon?.combat
  const stats = dungeon?.stats
  const skills = Object.values(dungeon?.skills ?? {})
  if (!combat) return null

  const enemy = combat.enemy
  const companion = combat.companion
  const usable = Object.entries(inventory).filter(([id]) =>
    ['food', 'booster'].includes(items?.[id]?.type),
  )
  const isBoss = enemy.role === 'boss'
  const charging = Boolean(combat.charging)

  const command = (action, extra) => {
    setMenu(null)
    act(action, extra)
  }

  return (
    <div className="battle-overlay" role="dialog" aria-label="Battle">
      <div className={`battle-window${isBoss ? ' battle-window--boss' : ''}`}>
        <header className="battle-top">
          <div className="battle-top-enemy">
            <strong>{enemy.name}</strong>
            {enemy.role !== 'normal' && <span className="battle-role">{enemy.role}</span>}
            <span className={`element element--${enemy.element}`}>{enemy.element}</span>
          </div>
          <span className="battle-turn">Turn {combat.turn}</span>
        </header>

        <div className="battle-msg" aria-live="polite">
          {combat.log.slice(-3).map((line, i) => (
            <p key={combat.log.length - 3 + i}>{line}</p>
          ))}
        </div>

        {charging && (
          <div className="battle-telegraph" role="alert">
            ⚠ {combat.charging.telegraph}
          </div>
        )}

        <div className="battle-field">
          <div className="battle-side battle-side--party">
            <Fighter
              name={player?.name || 'You'}
              icon={(player?.name || 'Y')[0].toUpperCase()}
              hp={combat.player_hp}
              maxHp={stats.max_hp}
              guarding={combat.guarding}
              effects={combat.player_effects}
            />
            {companion && (
              <Fighter
                name={companion.name}
                icon={ROLE_ICON[companion.role] ?? companion.name[0]}
                hp={companion.hp}
                maxHp={companion.max_hp}
                down={companion.down}
                sub={companion.role}
                element={companion.element}
                small
              />
            )}
          </div>

          <div className="battle-side battle-side--enemy">
            <div
              className={[
                'enemy-sprite',
                `enemy-sprite--${enemy.element}`,
                charging ? 'enemy-sprite--charging' : '',
                enemy.role !== 'normal' ? 'enemy-sprite--boss' : '',
              ].join(' ')}
            >
              <span className="enemy-glyph">{ENEMY_ICON[enemy.role] ?? '⚔'}</span>
            </div>
            <HpBar value={combat.enemy_hp} max={enemy.hp} kind="enemy" />
            <StatusChips effects={combat.enemy_effects} />
            <p className="battle-desc">{enemy.description}</p>
          </div>
        </div>

        <div className="battle-hud">
          <div className="battle-commands">
            {menu === 'skills' ? (
              <SubMenu onBack={() => setMenu(null)}>
                {skills.map((s) => (
                  <button
                    key={s.id}
                    className="battle-cmd"
                    disabled={busy || combat.charge < s.cost}
                    title={s.description}
                    onClick={() => command('skill', { skill_id: s.id })}
                  >
                    {s.name}
                    <span className={`cmd-meta element--${s.element}`}>
                      {s.element} · {s.cost}●
                    </span>
                  </button>
                ))}
              </SubMenu>
            ) : menu === 'items' ? (
              <SubMenu onBack={() => setMenu(null)}>
                {usable.map(([id, qty]) => (
                  <button
                    key={id}
                    className="battle-cmd"
                    disabled={busy}
                    title={items[id].description}
                    onClick={() => command('item', { item_id: id })}
                  >
                    {items[id].name}
                    <span className="cmd-meta">×{qty}</span>
                  </button>
                ))}
              </SubMenu>
            ) : (
              <>
                <button className="battle-cmd" disabled={busy} onClick={() => command('attack')}>
                  Attack
                </button>
                <button
                  className="battle-cmd"
                  disabled={busy || !skills.length}
                  onClick={() => setMenu('skills')}
                >
                  Skill <span className="cmd-arrow">▸</span>
                </button>
                <button
                  className="battle-cmd"
                  disabled={busy}
                  title={charging ? 'Braced: a read telegraph hits for 1/3' : 'Halve the next hit, +1 charge'}
                  onClick={() => command('guard')}
                >
                  Guard
                </button>
                <button
                  className="battle-cmd"
                  disabled={busy || !usable.length}
                  onClick={() => setMenu('items')}
                >
                  Item <span className="cmd-arrow">▸</span>
                </button>
                <button
                  className="battle-cmd"
                  disabled={busy || isBoss}
                  title={isBoss ? "Bosses won't let you leave" : ''}
                  onClick={() => command('flee')}
                >
                  Flee
                </button>
              </>
            )}
          </div>

          <div className="battle-party-status">
            <StatusRow
              name={player?.name || 'You'}
              hp={combat.player_hp}
              maxHp={stats.max_hp}
              effects={combat.player_effects}
              extra={
                <span className="battle-charge" title="Charge powers skills">
                  {'●'.repeat(combat.charge)}
                  {'○'.repeat(Math.max(0, (combat.charge_max ?? 5) - combat.charge))}
                </span>
              }
            />
            {companion && (
              <StatusRow
                name={companion.name}
                hp={companion.hp}
                maxHp={companion.max_hp}
                down={companion.down}
                extra={<span className="party-role">{companion.role}</span>}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function SubMenu({ children, onBack }) {
  return (
    <>
      {children}
      <button className="battle-cmd battle-cmd--back" onClick={onBack}>
        ◂ Back
      </button>
    </>
  )
}

function Fighter({ name, icon, hp, maxHp, down, guarding, sub, element, effects, small }) {
  return (
    <div className={`fighter${down ? ' fighter--down' : ''}${small ? ' fighter--small' : ''}`}>
      <div className={`fighter-sprite${element ? ` fighter-sprite--${element}` : ''}`}>
        <span className="fighter-glyph">{icon}</span>
        {guarding && <span className="fighter-guard" title="Guarding">⛉</span>}
      </div>
      <span className="fighter-name">
        {name}
        {sub && <span className="fighter-sub"> {sub}</span>}
      </span>
      {down ? (
        <span className="fighter-downtag">DOWN</span>
      ) : (
        <HpBar value={hp} max={maxHp} kind="you" slim />
      )}
      {effects && <StatusChips effects={effects} />}
    </div>
  )
}

function StatusRow({ name, hp, maxHp, down, effects, extra }) {
  return (
    <div className={`status-row${down ? ' status-row--down' : ''}`}>
      <span className="status-row-name">{name}</span>
      {down ? (
        <span className="fighter-downtag">DOWN</span>
      ) : (
        <HpBar value={hp} max={maxHp} kind="you" />
      )}
      <span className="status-row-extra">{extra}</span>
      {effects && <StatusChips effects={effects} />}
    </div>
  )
}

function HpBar({ value, max, kind, slim }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  const low = kind === 'you' && pct <= 25
  return (
    <div className={`hpbar${slim ? ' hpbar--slim' : ''}`}>
      <div className="hpbar-track">
        <span
          className={`hpbar-fill hpbar-fill--${kind}${low ? ' hpbar-fill--low' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="hpbar-num">
        {value}/{max}
      </span>
    </div>
  )
}
