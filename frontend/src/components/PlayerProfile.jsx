import { useGameStore } from '../state/gameStore'
import PreferenceTags from './PreferenceTags.jsx'

// The player's own opinions. Others don't know these until you reveal them
// in conversation.
export default function PlayerProfile() {
  const player = useGameStore((s) => s.state?.player)
  if (!player) return null

  return (
    <section className="player-profile">
      <h2>You</h2>
      <PreferenceTags preferences={player.preferences} empty="No strong opinions yet." />
    </section>
  )
}
