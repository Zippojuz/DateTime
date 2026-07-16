import { useGameStore } from '../state/gameStore'

// Where to? — the venue picker behind the People panel's "Ask out" button.
// Venue open/closed state is the server's call; a closed venue answers with
// its own line when you try.
export default function AskOutPicker() {
  const picker = useGameStore((s) => s.askOut)
  const dateVenues = useGameStore((s) => s.dateVenues)
  const startDate = useGameStore((s) => s.startDate)
  const closeAskOut = useGameStore((s) => s.closeAskOut)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  if (!picker || !dateVenues) return null

  return (
    <div className="battle-overlay" role="dialog" aria-label={`Ask ${picker.name} out`}>
      <div className="askout-window">
        <header className="dialogue-header">
          <span className="dialogue-npc">Ask {picker.name} out</span>
          <button className="dialogue-close" onClick={closeAskOut} aria-label="Never mind">
            ✕
          </button>
        </header>
        {error && <p className="form-error">{error}</p>}
        <ul className="askout-list">
          {Object.values(dateVenues).map((v) => (
            <li key={v.venue} className="askout-item">
              <div className="askout-info">
                <span className="askout-title">{v.title}</span>
                <span className="askout-sub">
                  {v.cost}cr · {Math.floor(v.minutes / 60)}h
                  {v.minutes % 60 ? ` ${v.minutes % 60}m` : ''} · you cover both
                </span>
              </div>
              <button
                className="btn-action"
                disabled={busy}
                onClick={() => startDate(picker.npcId, v.venue)}
              >
                Ask
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
