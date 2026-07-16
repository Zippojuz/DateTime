import { useGameStore } from '../state/gameStore'
import RarityTag from './RarityTag.jsx'

function StockList({ stock, credits, busy, buyItem }) {
  return (
    <ul className="shop-list">
      {stock.map((item) => (
        <li key={item.id} className="shop-item">
          <div className="shop-info">
            <span className="shop-name">
              {item.name} <RarityTag rarity={item.rarity} />
              {item.tonight && <span className="shop-tonight">✶ tonight only</span>}
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
  )
}

// The market in your current district. Prices scale with rarity + a district
// modifier; browsing costs a little game time. Black-market back rooms
// (cred_tiers) unlock as your street cred grows — locked ones only tease.
export default function ShopPanel() {
  const shop = useGameStore((s) => s.shop)
  const buyItem = useGameStore((s) => s.buyItem)
  const marketGossip = useGameStore((s) => s.marketGossip)
  const lastGossip = useGameStore((s) => s.lastGossip)
  const credits = useGameStore((s) => s.state?.player?.credits ?? 0)
  const cred = useGameStore((s) => s.state?.player?.street_cred ?? 0)
  const busy = useGameStore((s) => s.busy)

  if (!shop || !shop.stock?.length) return null

  return (
    <section className="shop-panel">
      <h2>{shop.name ?? 'Shop'}</h2>
      {shop.blurb && <p className="shop-blurb">{shop.blurb}</p>}
      {lastGossip && <p className="shop-gossip">{lastGossip.text}</p>}
      {shop.gossip_available && (
        <button className="btn-action shop-gossip-btn" disabled={busy} onClick={marketGossip}>
          Ask around · 15m
        </button>
      )}
      <StockList stock={shop.stock} credits={credits} busy={busy} buyItem={buyItem} />

      {(shop.tiers ?? []).map((tier) =>
        tier.unlocked ? (
          <div key={tier.name} className="shop-tier">
            <h3 className="shop-tier-name">{tier.name}</h3>
            <StockList stock={tier.stock} credits={credits} busy={busy} buyItem={buyItem} />
          </div>
        ) : (
          <div key={tier.name} className="shop-tier shop-tier--locked">
            <h3 className="shop-tier-name">
              🔒 {tier.name}
              <span className="shop-tier-req">
                {' '}
                opens at {tier.cred} cred (you: {cred})
              </span>
            </h3>
            <p className="shop-tier-tease">{tier.tease}</p>
          </div>
        ),
      )}
    </section>
  )
}
