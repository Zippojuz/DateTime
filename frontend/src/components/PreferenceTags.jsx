import { useGameStore } from '../state/gameStore'

// Sentiment → display. Shared by the player's own profile and the (discovered)
// preferences shown for NPCs.
const SENTIMENT = {
  love: { symbol: '♥♥', className: 'pref--love', label: 'loves' },
  like: { symbol: '♥', className: 'pref--like', label: 'likes' },
  dislike: { symbol: '✕', className: 'pref--dislike', label: 'dislikes' },
  hate: { symbol: '✕✕', className: 'pref--hate', label: 'hates' },
}

export default function PreferenceTags({ preferences, empty = 'Nothing known yet.' }) {
  const topics = useGameStore((s) => s.topics)
  const entries = Object.entries(preferences ?? {})

  if (!entries.length) return <span className="pref-empty">{empty}</span>

  return (
    <span className="pref-tags">
      {entries.map(([topicId, pref]) => {
        const s = SENTIMENT[pref.sentiment]
        const name = topics?.[topicId]?.name ?? topicId
        if (!s) return null
        return (
          <span key={topicId} className={`pref ${s.className}`} title={s.label}>
            {name} {s.symbol}
            {pref.changeable === false && <span className="pref-core"> ·core</span>}
          </span>
        )
      })}
    </span>
  )
}
