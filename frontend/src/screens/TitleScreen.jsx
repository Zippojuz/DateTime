import { useEffect } from 'react'
import { useGameStore } from '../state/gameStore'

// Milestone 0 deliverable: the title screen confirms it reached the backend's
// /api/health endpoint.
export default function TitleScreen() {
  const connection = useGameStore((s) => s.connection)
  const connectionError = useGameStore((s) => s.connectionError)
  const checkConnection = useGameStore((s) => s.checkConnection)

  useEffect(() => {
    checkConnection()
  }, [checkConnection])

  return (
    <main className="title-screen">
      <h1 className="title-logo">NEXUS CITY</h1>
      <p className="title-tagline">A ship. A debt. A city that never sleeps.</p>

      <div className={`server-status server-status--${connection}`} role="status">
        {connection === 'unknown' && 'Reaching Nexus core…'}
        {connection === 'ok' && 'Connected to Nexus core'}
        {connection === 'error' && `Offline — ${connectionError}`}
      </div>

      <button className="btn-primary" disabled>
        New Game <span className="btn-hint">(Milestone 1)</span>
      </button>
    </main>
  )
}
