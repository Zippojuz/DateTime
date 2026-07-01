import { useGameStore } from '../state/gameStore'

// Landing screen. Confirms the backend connection and offers New Game /
// Continue depending on whether a save exists.
export default function TitleScreen() {
  const connection = useGameStore((s) => s.connection)
  const connectionError = useGameStore((s) => s.connectionError)
  const hasSave = useGameStore((s) => s.hasSave)
  const startCreation = useGameStore((s) => s.startCreation)
  const continueGame = useGameStore((s) => s.continueGame)

  const ready = connection === 'ok'

  return (
    <main className="title-screen">
      <h1 className="title-logo">NEXUS CITY</h1>
      <p className="title-tagline">A ship. A debt. A city that never sleeps.</p>

      <div className={`server-status server-status--${connection}`} role="status">
        {connection === 'unknown' && 'Reaching Nexus core…'}
        {connection === 'ok' && 'Connected to Nexus core'}
        {connection === 'error' && `Offline — ${connectionError}`}
      </div>

      <div className="title-actions">
        {hasSave && (
          <button className="btn-primary" onClick={continueGame} disabled={!ready}>
            Continue
          </button>
        )}
        <button className="btn-primary" onClick={startCreation} disabled={!ready}>
          New Game
        </button>
      </div>
    </main>
  )
}
