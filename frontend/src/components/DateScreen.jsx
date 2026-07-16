import { useGameStore } from '../state/gameStore'

// THE DATING SYSTEM's stage: an outing plays as a scene overlay — opening,
// choice beats with the date's reactions, then a closing that tells you how
// the evening actually went.
export default function DateScreen() {
  const date = useGameStore((s) => s.date)
  const chooseDateBeat = useGameStore((s) => s.chooseDateBeat)
  const leaveDate = useGameStore((s) => s.leaveDate)
  const closeDate = useGameStore((s) => s.closeDate)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  if (!date) return null

  return (
    <div className="dialogue-overlay" role="dialog" aria-label={`Out with ${date.npc_name}`}>
      <div className="dialogue-box date-box">
        <header className="dialogue-header">
          <span className="dialogue-npc">{date.title}</span>
          {date.gained > 0 && <span className="dialogue-affection">+{date.gained} ♥</span>}
          {!date.done && (
            <button className="dialogue-close" onClick={leaveDate} aria-label="Leave the date">
              ✕
            </button>
          )}
        </header>

        {date.opening && <p className="date-opening">{date.opening}</p>}
        {date.reply && <p className="date-reply">{date.reply}</p>}

        {error && <p className="form-error">{error}</p>}

        {!date.done ? (
          <>
            <p className="dialogue-text">{date.text}</p>
            <p className="date-progress">
              {date.beat + 1} / {date.total_beats}
            </p>
            <ul className="dialogue-choices">
              {date.choices.map((choice) => (
                <li key={choice.index}>
                  <button
                    className="dialogue-choice"
                    disabled={busy}
                    onClick={() => chooseDateBeat(choice.index)}
                  >
                    {choice.text}
                  </button>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <>
            <p className="dialogue-text">{date.closing}</p>
            {!date.left && (
              <p className="date-verdict">
                {date.good ? 'It went well.' : 'It went… fine.'} +{date.gained} ♥
              </p>
            )}
            <button className="btn-action" onClick={closeDate}>
              Head home
            </button>
          </>
        )}
      </div>
    </div>
  )
}
