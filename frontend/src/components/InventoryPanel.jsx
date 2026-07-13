import { useGameStore } from '../state/gameStore'
import RarityTag from './RarityTag.jsx'

// What you're carrying. Food can be used (restores energy); gifts are given via
// the People panel.
export default function InventoryPanel() {
  const inventory = useGameStore((s) => s.state?.player?.inventory)
  const items = useGameStore((s) => s.items)
  const useItem = useGameStore((s) => s.useItem)
  const busy = useGameStore((s) => s.busy)

  if (!inventory || !items) return null
  const entries = Object.entries(inventory)

  return (
    <section className="inventory-panel">
      <h2>Inventory</h2>
      {entries.length === 0 ? (
        <p className="inv-empty">Empty. Try a shop.</p>
      ) : (
        <ul className="inv-list">
          {entries.map(([id, qty]) => {
            const item = items[id]
            if (!item) return null
            return (
              <li key={id} className="inv-item">
                <div className="inv-info">
                  <span className="inv-name">
                    {item.name} ×{qty} <RarityTag rarity={item.rarity} />
                  </span>
                  <span className="inv-sub">{item.description}</span>
                </div>
                {item.type === 'food' && (
                  <button className="btn-action" disabled={busy} onClick={() => useItem(id)}>
                    Use
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
