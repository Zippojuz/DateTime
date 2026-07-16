import { useState } from 'react'
import { useGameStore } from '../state/gameStore'
import InventoryPanel from './InventoryPanel.jsx'

const TABS = ['Messages', 'Inventory', 'Settings']

// The Cyberlink — standard-issue neural interface. The game's device layer:
// remote messages to known contacts, the inventory ledger, and settings all
// live "on the link". Everyone has one. Nobody read the EULA.
export default function CyberlinkModal() {
  const open = useGameStore((s) => s.linkOpen)
  const closeLink = useGameStore((s) => s.closeLink)
  const [tab, setTab] = useState('Messages')

  if (!open) return null

  return (
    <div className="battle-overlay" role="dialog" aria-label="Cyberlink">
      <div className="link-window">
        <header className="link-head">
          <span className="link-brand">⬡ CYBERLINK</span>
          <nav className="link-tabs">
            {TABS.map((t) => (
              <button
                key={t}
                className={`chip ${tab === t ? 'chip--active' : ''}`}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
          </nav>
          <button className="btn-action" onClick={closeLink}>
            Close
          </button>
        </header>

        {tab === 'Messages' && <MessagesTab />}
        {tab === 'Inventory' && <InventoryPanel />}
        {tab === 'Settings' && <SettingsTab />}
      </div>
    </div>
  )
}

function MessagesTab() {
  const characters = useGameStore((s) => s.characters)
  const tones = useGameStore((s) => s.linkTones)
  const sendMessage = useGameStore((s) => s.sendMessage)
  const lastMessage = useGameStore((s) => s.lastMessage)
  const busy = useGameStore((s) => s.busy)

  const contacts = characters.filter((c) => c.met)

  if (!contacts.length) {
    return (
      <p className="link-empty">
        No contacts yet. The link needs a handshake — go talk to someone in person.
      </p>
    )
  }

  return (
    <div className="link-messages">
      {lastMessage && (
        <div className="link-reply">
          <span className="link-reply-from">{lastMessage.npc}</span>
          <p>{lastMessage.reply}</p>
          {lastMessage.gained > 0 && <span className="link-gained">+{lastMessage.gained}</span>}
        </div>
      )}
      <ul className="link-contacts">
        {contacts.map((c) => (
          <li key={c.id} className="link-contact">
            <div className="link-contact-info">
              <strong>{c.name}</strong>
              <span className="link-stage">{c.stage}</span>
            </div>
            <div className="link-tones">
              {c.messaged_today ? (
                <span className="link-cooldown">pinged today — let it breathe</span>
              ) : (
                Object.entries(tones ?? {}).map(([id, tone]) => (
                  <button
                    key={id}
                    className="btn-action"
                    disabled={busy}
                    onClick={() => sendMessage(c.id, id)}
                  >
                    {tone.label}
                  </button>
                ))
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function SettingsTab() {
  const player = useGameStore((s) => s.state?.player)
  const species = useGameStore((s) => s.species)
  const link = useGameStore((s) => s.items?.cyberlink)
  const difficulties = useGameStore((s) => s.difficulties)
  const setDifficulty = useGameStore((s) => s.setDifficulty)
  const busy = useGameStore((s) => s.busy)

  if (!player) return null
  const trait = species?.[player.trait]?.trait

  return (
    <div className="link-settings">
      <h3>This unit</h3>
      <p className="link-unit">
        <strong>{player.identity.name}</strong> · {player.identity.pronouns} · {player.species}
        {trait && (
          <>
            {' '}
            · <span className="player-trait-name">{trait.name}</span>
          </>
        )}
      </p>
      {link && <p className="link-eula">{link.description}</p>}

      <h3>Difficulty</h3>
      <div className="link-difficulty">
        {Object.entries(difficulties ?? {}).map(([id, d]) => (
          <button
            key={id}
            className={`chip ${player.difficulty === id ? 'chip--active' : ''}`}
            title={d.description}
            disabled={busy}
            onClick={() => setDifficulty(id)}
          >
            {d.name}
          </button>
        ))}
      </div>
    </div>
  )
}
