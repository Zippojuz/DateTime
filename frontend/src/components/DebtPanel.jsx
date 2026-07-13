import { useState } from 'react'
import { useGameStore } from '../state/gameStore'

// The debt that brought you to Nexus City. Pay it down with credits earned from
// jobs before it comes due.
export default function DebtPanel() {
  const player = useGameStore((s) => s.state?.player)
  const payDebt = useGameStore((s) => s.payDebt)
  const busy = useGameStore((s) => s.busy)
  const [amount, setAmount] = useState('')

  if (!player) return null
  const max = Math.min(player.credits, player.debt)

  const submit = (e) => {
    e.preventDefault()
    const n = parseInt(amount, 10)
    if (n > 0) {
      payDebt(n)
      setAmount('')
    }
  }

  return (
    <section className="debt-panel">
      <h2>The Debt</h2>
      {player.debt > 0 ? (
        <>
          <p className="debt-status">
            <strong>{player.debt} cr</strong> owed · due by week {player.debt_due_week}
          </p>
          <form className="debt-form" onSubmit={submit}>
            <input
              type="number"
              min="1"
              max={max}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder={`up to ${max}`}
              disabled={busy || max <= 0}
            />
            <button className="btn-action" type="submit" disabled={busy || max <= 0}>
              Pay
            </button>
            <button
              type="button"
              className="btn-action"
              disabled={busy || max <= 0}
              onClick={() => payDebt(max)}
            >
              Pay {max}
            </button>
          </form>
        </>
      ) : (
        <p className="debt-status">Paid in full. You're free.</p>
      )}
    </section>
  )
}
