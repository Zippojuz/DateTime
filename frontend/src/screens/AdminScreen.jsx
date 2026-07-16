import { useState } from 'react'
import { useGameStore } from '../state/gameStore'

// The admin desk: every account, their city, and the live-ops tools —
// comp credits, unstick a save, delete an account. Admins only (the server
// checks; this screen just doesn't render for anyone else).
export default function AdminScreen() {
  const admin = useGameStore((s) => s.admin)
  const user = useGameStore((s) => s.user)
  const closeAdmin = useGameStore((s) => s.closeAdmin)
  const adminComp = useGameStore((s) => s.adminComp)
  const adminUnstick = useGameStore((s) => s.adminUnstick)
  const adminDelete = useGameStore((s) => s.adminDelete)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  const [confirming, setConfirming] = useState(null)

  return (
    <main className="admin-screen">
      <header className="admin-head">
        <h1>Admin — Players</h1>
        <button className="btn-action" onClick={closeAdmin}>
          Back
        </button>
      </header>
      {error && <p className="form-error">{error}</p>}
      {!admin ? (
        <p className="admin-empty">Loading the roster…</p>
      ) : (
        <ul className="admin-list">
          {admin.map((row) => (
            <li key={row.user_id} className="admin-row">
              <div className="admin-who">
                <strong>
                  {row.username}
                  {row.is_admin && <span className="admin-badge"> admin</span>}
                </strong>
                <span className="admin-sub">
                  {row.save
                    ? `${row.save.name} · ${row.save.species} · week ${row.save.week} · ` +
                      `${row.save.credits} cr · ${row.save.location} · energy ${row.save.energy}`
                    : 'no save yet'}
                </span>
                <span className="admin-sub">last seen {row.last_seen}</span>
              </div>
              <div className="admin-actions">
                <button
                  className="btn-action"
                  disabled={busy || !row.save}
                  title="Grant 100 credits"
                  onClick={() => adminComp(row.user_id, 100)}
                >
                  Comp 100cr
                </button>
                <button
                  className="btn-action"
                  disabled={busy || !row.save}
                  title="Clear scene state, send home, full energy"
                  onClick={() => adminUnstick(row.user_id)}
                >
                  Unstick
                </button>
                {confirming === row.user_id ? (
                  <button
                    className="btn-action admin-danger"
                    disabled={busy}
                    onClick={() => {
                      adminDelete(row.user_id)
                      setConfirming(null)
                    }}
                  >
                    Really delete
                  </button>
                ) : (
                  <button
                    className="btn-action"
                    disabled={busy || row.username === user?.username}
                    title={
                      row.username === user?.username
                        ? 'Not from inside the chair'
                        : 'Delete account and save'
                    }
                    onClick={() => setConfirming(row.user_id)}
                  >
                    Delete
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  )
}
