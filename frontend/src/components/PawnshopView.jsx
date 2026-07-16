import { useGameStore } from '../state/gameStore'
import RarityTag from './RarityTag.jsx'

// Forget-Me-Not — selling, finally. The broker quotes everything you carry;
// what you pawn waits on the shelf for buyback until the hold runs out.
export default function PawnshopView() {
  const state = useGameStore((s) => s.state)
  const pawn = useGameStore((s) => s.pawn)
  const items = useGameStore((s) => s.items)
  const sellItem = useGameStore((s) => s.sellItem)
  const buybackItem = useGameStore((s) => s.buybackItem)
  const lastPawn = useGameStore((s) => s.lastPawn)
  const busy = useGameStore((s) => s.busy)

  if (state?.player?.location !== 'forget_me_not' || !pawn || !items) return null
  const inventory = state.player.inventory ?? {}
  const sellable = Object.entries(pawn.offers ?? {}).filter(([id]) => inventory[id] > 0)

  return (
    <section className="pawnshop-view">
      <h2>Forget-Me-Not</h2>
      {lastPawn && <p className="pawn-line">{lastPawn.line}</p>}

      <h3>The counter</h3>
      {sellable.length === 0 ? (
        <p className="pawn-empty">
          The broker looks over what you&apos;re carrying and shrugs, kindly. Nothing they can
          shelve.
        </p>
      ) : (
        <ul className="pawn-list">
          {sellable.map(([id, offer]) => {
            const item = items[id]
            return (
              <li key={id} className="pawn-item">
                <div className="pawn-info">
                  <span>
                    {item?.name} ×{inventory[id]} <RarityTag rarity={item?.rarity} />
                  </span>
                  <span className="pawn-sub">{item?.description}</span>
                </div>
                <button className="btn-action" disabled={busy} onClick={() => sellItem(id)}>
                  Pawn · {offer}cr
                </button>
              </li>
            )
          })}
        </ul>
      )}

      <h3>The shelf</h3>
      {pawn.shelf.length === 0 ? (
        <p className="pawn-empty">Nothing of yours on the shelf. The ledger approves.</p>
      ) : (
        <ul className="pawn-list">
          {pawn.shelf.map((entry, i) => (
            <li key={`${entry.item}-${i}`} className="pawn-item pawn-item--held">
              <div className="pawn-info">
                <span>{entry.name}</span>
                <span className="pawn-sub">
                  {entry.days_left} day{entry.days_left === 1 ? '' : 's'} before it&apos;s sold on
                </span>
              </div>
              <button className="btn-action" disabled={busy} onClick={() => buybackItem(i)}>
                Buy back · {entry.buyback}cr
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="pawn-backcase">
        The locked back case sits behind the grate: MEMORIES — BY APPOINTMENT ONLY.
      </p>
    </section>
  )
}
