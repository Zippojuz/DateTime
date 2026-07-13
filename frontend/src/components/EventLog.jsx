import { useGameStore } from '../state/gameStore'

// Seasonal / story events that have fired, shown until acknowledged.
export default function EventLog() {
  const events = useGameStore((s) => s.pendingEvents)
  const dismiss = useGameStore((s) => s.dismissEvent)

  if (!events.length) return null

  return (
    <div className="event-log">
      {events.map((ev) => (
        <div key={ev.id} className={`event-card event-card--${ev.type}`} role="status">
          <span className="event-type">{ev.type}</span>
          <h3 className="event-title">{ev.title}</h3>
          <p className="event-text">{ev.text}</p>
          <button
            className="event-dismiss"
            onClick={() => dismiss(ev.id)}
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
