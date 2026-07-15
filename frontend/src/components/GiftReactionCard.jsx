import { useGameStore } from '../state/gameStore'

// Each line is a standalone sentence (subject "Their"/"They") so it never has
// to double up on the gift as a grammatical object — the item gets its own
// clause instead.
const SENTIMENT_LINE = {
  love: 'Their face lights up.',
  like: 'They seem genuinely pleased.',
  neutral: 'They accept it politely.',
  dislike: 'They take it with a faint frown.',
  hate: "They're clearly put off.",
}

// Toast shown after giving a gift.
export default function GiftReactionCard() {
  const r = useGameStore((s) => s.lastReaction)
  const dismiss = useGameStore((s) => s.dismissReaction)

  if (!r) return null
  const sign = r.delta >= 0 ? '+' : ''

  return (
    <div className="encounter-card" role="status">
      <span className="encounter-kind">gift</span>
      <p className="encounter-text">
        You give {r.npcName} the {r.item}. {SENTIMENT_LINE[r.sentiment] ?? 'They react.'}
      </p>
      <span className={`encounter-affection ${r.delta < 0 ? 'is-neg' : ''}`}>
        {sign}
        {r.delta} ♥
      </span>
      <button className="encounter-dismiss" onClick={dismiss} aria-label="Dismiss">
        ✕
      </button>
    </div>
  )
}
