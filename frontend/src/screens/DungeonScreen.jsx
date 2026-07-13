import { useGameStore } from '../state/gameStore'
import BattleView from '../components/BattleView.jsx'

const ROOM_ICON = {
  battle: '⚔',
  miniboss: '☠',
  boss: '♛',
  event: '?',
  treasure: '◆',
  rest: '✚',
  unknown: '·',
}

// The Substrate. Shows floor/room progress and the current room's content;
// battles render the BattleView, events render their choices.
export default function DungeonScreen() {
  const dungeon = useGameStore((s) => s.dungeon)
  const result = useGameStore((s) => s.dungeonResult)
  const advance = useGameStore((s) => s.advanceDungeon)
  const leave = useGameStore((s) => s.leaveDungeon)
  const chooseEvent = useGameStore((s) => s.chooseDungeonEvent)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  const run = dungeon?.run
  const combat = dungeon?.combat
  const stats = dungeon?.stats
  if (!run) return null

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

      <div className="dungeon-rooms" aria-label="Floor progress">
        {run.rooms.map((room, i) => (
          <span
            key={i}
            className={`droom ${i === run.room ? 'droom--here' : ''} ${room.done ? 'droom--done' : ''}`}
            title={room.type}
          >
            {ROOM_ICON[room.type] ?? '·'}
          </span>
        ))}
      </div>

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
          {result && <p className="dungeon-text">{result.text}</p>}
          {run.cleared ? (
            <p className="dungeon-text">
              You've reached the bottom of the Substrate — for now.
            </p>
          ) : null}
          <div className="dungeon-actions">
            {!run.cleared && (
              <button className="btn-primary" disabled={busy} onClick={advance}>
                Press deeper
              </button>
            )}
            <button className="btn-action" disabled={busy} onClick={leave}>
              Leave the Substrate
            </button>
          </div>
        </section>
      )}
    </main>
  )
}
