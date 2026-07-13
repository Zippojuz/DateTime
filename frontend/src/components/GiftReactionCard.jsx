import { useGameStore } from '../state/gameStore'

const SENTIMENT_LINE = {
  love: 'lights up',
  like: 'seems genuinely pleased',
  neutral: 'accepts it politely',
  dislike: 'takes it with a faint frown',
  hate: 'is clearly put off',
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
        {r.npcName} {SENTIMENT_LINE[r.sentiment] ?? 'reacts'} to the {r.item}.
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
