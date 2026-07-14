import { useGameStore } from '../state/gameStore'
import BattleView from '../components/BattleView.jsx'

const ROOM_ICON = {
  stairs_up: '▲',
  stairs_down: '▼',
  battle: '⚔',
  miniboss: '☠',
  boss: '♛',
  event: '?',
  treasure: '◆',
  cache: '✦',
  rest: '✚',
  keycard: '⚿',
  generator: '⚡',
  empty: '·',
}

const DIR_ARROW = { n: '↑', e: '→', s: '↓', w: '←' }

// The Substrate, Zork-style: a fog-of-war map that draws itself as you explore,
// a room description, compass exits with flavor, Search, and context actions.
export default function DungeonScreen() {
  const dungeon = useGameStore((s) => s.dungeon)
  const result = useGameStore((s) => s.dungeonResult)
  const move = useGameStore((s) => s.moveDungeon)
  const search = useGameStore((s) => s.searchDungeon)
  const interact = useGameStore((s) => s.interactDungeon)
  const leave = useGameStore((s) => s.leaveDungeon)
  const chooseEvent = useGameStore((s) => s.chooseDungeonEvent)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  const run = dungeon?.run
  const combat = dungeon?.combat
  const stats = dungeon?.stats
  if (!run) return null

  const here = run.here
  const pendingEvent = run.pending_event_data

  return (
    <main className="dungeon-screen">
      <header className="dungeon-head">
        <div>
          <h1 className="dungeon-title">The Substrate</h1>
          <span className="dungeon-floor">Floor {run.floor}</span>
        </div>
        <div className="dungeon-player">
          <span>
            Lv {stats.level} · HP {combat ? combat.player_hp : run.player_hp}/{stats.max_hp}
          </span>
          <span className="dungeon-xp">
            XP {useGameStore.getState().state?.player?.combat_xp ?? 0}/{dungeon.xp_to_next}
          </span>
        </div>
      </header>

      <FloorMap map={run.map} />

      {error && <p className="form-error">{error}</p>}

      {combat ? (
        <BattleView />
      ) : pendingEvent ? (
        <section className="dungeon-card">
          <p className="dungeon-text">{pendingEvent.text}</p>
          <div className="dungeon-choices">
            {pendingEvent.choices.map((c, i) => (
              <button
                key={i}
                className="dialogue-choice"
                disabled={busy}
                onClick={() => chooseEvent(i)}
              >
                {c.text}
                {c.cost ? ` (${c.cost} cr)` : ''}
              </button>
            ))}
          </div>
        </section>
      ) : (
        <section className="dungeon-card">
          <h2 className="room-name">{here.name}</h2>
          <p className="dungeon-text">{here.desc}</p>
          {result?.text && <p className="dungeon-result">{result.text}</p>}
          {here.stairs_note && <p className="dungeon-note">{here.stairs_note}</p>}
          {here.hints.map((hint, i) => (
            <p key={i} className="dungeon-hint">
              {hint}
            </p>
          ))}
          {run.cleared && (
            <p className="dungeon-text">
              You've reached the bottom of the Substrate — for now.
            </p>
          )}

          <div className="dungeon-exits">
            {here.exits.map((e) => (
              <button
                key={e.dir}
                className="btn-action exit-btn"
                disabled={busy}
                title={e.known ? 'You know where this leads.' : 'Unexplored.'}
                onClick={() => move(e.dir)}
              >
                {DIR_ARROW[e.dir]} {e.word} <span className="exit-label">{e.label}</span>
              </button>
            ))}
          </div>

          <div className="dungeon-actions">
            {here.interact && (
              <button className="btn-primary" disabled={busy} onClick={interact}>
                {here.interact}
              </button>
            )}
            <button className="btn-action" disabled={busy} onClick={search}>
              Search the room
            </button>
            <button className="btn-action" disabled={busy} onClick={leave}>
              Leave the Substrate
            </button>
          </div>
        </section>
      )}
    </main>
  )
}

function FloorMap({ map }) {
  if (!map?.length) return null
  const xs = map.map((r) => r.x)
  const ys = map.map((r) => r.y)
  const minX = Math.min(...xs)
  const minY = Math.min(...ys)
  const cols = Math.max(...xs) - minX + 1
  const rows = Math.max(...ys) - minY + 1

  return (
    <div
      className="floor-map"
      style={{
        gridTemplateColumns: `repeat(${cols}, 2.2rem)`,
        gridTemplateRows: `repeat(${rows}, 2.2rem)`,
      }}
      aria-label="Floor map"
    >
      {map.map((room) => (
        <span
          key={room.id}
          className={[
            'map-room',
            room.stub ? 'map-room--stub' : '',
            room.current ? 'map-room--here' : '',
            room.resolved ? 'map-room--done' : '',
          ].join(' ')}
          style={{ gridColumn: room.x - minX + 1, gridRow: room.y - minY + 1 }}
          title={room.stub ? 'Unexplored' : room.name}
        >
          {room.stub ? '?' : (ROOM_ICON[room.type] ?? '·')}
        </span>
      ))}
    </div>
  )
}
