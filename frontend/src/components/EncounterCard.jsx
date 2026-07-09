import { useGameStore } from '../state/gameStore'

// Brief card shown after travel when a street encounter occurred.
export default function EncounterCard() {
  const encounter = useGameStore((s) => s.lastEncounter)
  const dismiss = useGameStore((s) => s.dismissEncounter)

  if (!encounter) return null

  return (
    <div className="encounter-card" role="status">
      <span className={`encounter-kind encounter-kind--${encounter.type}`}>
        {encounter.type}
      </span>
      <p className="encounter-text">{encounter.text}</p>
      {encounter.affection > 0 && (
        <span className="encounter-affection">+{encounter.affection} ♥</span>
      )}
      <button className="encounter-dismiss" onClick={dismiss} aria-label="Dismiss">
        ✕
      </button>
    </div>
  )
}
