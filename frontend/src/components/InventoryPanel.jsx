import { useGameStore } from '../state/gameStore'
import RarityTag from './RarityTag.jsx'

// What you're carrying. Food can be used (restores energy); gifts are given via
// the People panel; gear equips into the Equipment panel.
export default function InventoryPanel() {
  const inventory = useGameStore((s) => s.state?.player?.inventory)
  const items = useGameStore((s) => s.items)
  const useItem = useGameStore((s) => s.useItem)
  const equipItem = useGameStore((s) => s.equipItem)
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
                    {item.dungeon_only && <span className="inv-substrate">substrate</span>}
                  </span>
                  <span className="inv-sub">{item.description}</span>
                </div>
                {item.type === 'food' && (
                  <button className="btn-action" disabled={busy} onClick={() => useItem(id)}>
                    Use
                  </button>
                )}
                {item.type === 'shard' && (
                  <button
                    className="btn-action"
                    disabled={busy}
                    title="Burn this protocol into your lace (consumed)"
                    onClick={() => useItem(id)}
                  >
                    Learn
                  </button>
                )}
                {(item.type === 'equipment' || item.type === 'augment') && (
                  <button className="btn-action" disabled={busy} onClick={() => equipItem(id)}>
                    {item.type === 'augment' ? 'Install' : 'Equip'}
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
