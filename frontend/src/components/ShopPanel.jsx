import { useGameStore } from '../state/gameStore'
import RarityTag from './RarityTag.jsx'

// The market in your current district. Prices scale with rarity + a district
// modifier; browsing costs a little game time.
export default function ShopPanel() {
  const shop = useGameStore((s) => s.shop)
  const buyItem = useGameStore((s) => s.buyItem)
  const credits = useGameStore((s) => s.state?.player?.credits ?? 0)
  const busy = useGameStore((s) => s.busy)

  if (!shop || !shop.stock?.length) return null

  return (
    <section className="shop-panel">
      <h2>{shop.name ?? 'Shop'}</h2>
      <ul className="shop-list">
        {shop.stock.map((item) => (
          <li key={item.id} className="shop-item">
            <div className="shop-info">
              <span className="shop-name">
                {item.name} <RarityTag rarity={item.rarity} />
              </span>
              <span className="shop-sub">{item.description}</span>
            </div>
            <button
              className="btn-action"
              disabled={busy || credits < item.price}
              title={credits < item.price ? 'Not enough credits' : ''}
              onClick={() => buyItem(item.id)}
            >
              {item.price} cr
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
