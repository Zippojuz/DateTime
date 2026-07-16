import { useState } from 'react'
import { useGameStore } from '../state/gameStore'

// The door. Accounts are for the save, not the character — your username
// isn't your name in the city (that's what the creation screen is for).
export default function LoginScreen() {
  const loginAccount = useGameStore((s) => s.loginAccount)
  const registerAccount = useGameStore((s) => s.registerAccount)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const submit = (e) => {
    e.preventDefault()
    if (mode === 'login') loginAccount(username, password)
    else registerAccount(username, password)
  }

  return (
    <main className="title-screen">
      <h1 className="title-logo">NEXUS CITY</h1>
      <p className="title-tagline">A ship. A debt. A city that never sleeps.</p>

      <form className="login-form" onSubmit={submit}>
        <div className="login-tabs">
          <button
            type="button"
            className={`chip ${mode === 'login' ? 'chip--active' : ''}`}
            onClick={() => setMode('login')}
          >
            Log in
          </button>
          <button
            type="button"
            className={`chip ${mode === 'register' ? 'chip--active' : ''}`}
            onClick={() => setMode('register')}
          >
            New account
          </button>
        </div>
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            maxLength={24}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button className="btn-primary" type="submit" disabled={busy || !username || !password}>
          {mode === 'login' ? 'Enter the city' : 'Register'}
        </button>
        <p className="login-note">
          Your username is for the save file. Who you are in the city comes later.
        </p>
      </form>
    </main>
  )
}
