import { useGameStore } from '../state/gameStore'

// Renders energy + attributes generically from the registry, so attributes
// added to data/attributes.json show up here automatically with no code change.
export default function StatBar() {
  const player = useGameStore((s) => s.state?.player)
  const registry = useGameStore((s) => s.attributes)

  if (!player) return null

  return (
    <div className="stat-bar">
      <div className="stat">
        <span className="stat-label">Level</span>
        <span className="stat-value">{player.combat_level}</span>
      </div>
      <div className="stat">
        <span className="stat-label">Energy</span>
        <span className="stat-meter">
          <span className="stat-fill" style={{ width: `${player.energy}%` }} />
        </span>
        <span className="stat-value">{player.energy}</span>
      </div>
      <div className="stat">
        <span className="stat-label stat-label--cred" title="Street cred — championships and depth records make you a name">
          Cred
        </span>
        <span className="stat-value">{player.street_cred ?? 0}</span>
      </div>

      {Object.entries(player.attributes).map(([id, value]) => (
        <div className="stat" key={id}>
          <span className="stat-label" title={registry?.[id]?.description}>
            {registry?.[id]?.name ?? id}
          </span>
          <span className="stat-value">{value}</span>
        </div>
      ))}
    </div>
  )
}
