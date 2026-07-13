import { useGameStore } from '../state/gameStore'
import RarityTag from './RarityTag.jsx'

// Overlay for choosing which item to give. Opened from the People panel.
export default function GiftPicker() {
  const gifting = useGameStore((s) => s.gifting)
  const inventory = useGameStore((s) => s.state?.player?.inventory)
  const items = useGameStore((s) => s.items)
  const giveGift = useGameStore((s) => s.giveGift)
  const cancel = useGameStore((s) => s.cancelGift)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  if (!gifting) return null
  const entries = Object.entries(inventory ?? {})

  return (
    <div className="dialogue-overlay" role="dialog" aria-label={`Give a gift to ${gifting.npcName}`}>
      <div className="dialogue-box">
        <header className="dialogue-header">
          <span className="dialogue-npc">Gift to {gifting.npcName}</span>
          <button className="dialogue-close" onClick={cancel} aria-label="Cancel">
            ✕
          </button>
        </header>
        {error && <p className="form-error">{error}</p>}
        {entries.length === 0 ? (
          <p className="inv-empty">You have nothing to give. Visit a shop first.</p>
        ) : (
          <ul className="gift-list">
            {entries.map(([id, qty]) => {
              const item = items?.[id]
              if (!item) return null
              return (
                <li key={id}>
                  <button
                    className="dialogue-choice"
                    disabled={busy}
                    onClick={() => giveGift(id)}
                  >
                    {item.name} ×{qty} <RarityTag rarity={item.rarity} />
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
