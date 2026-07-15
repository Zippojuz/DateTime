import { useGameStore } from '../state/gameStore'
import PreferenceTags from './PreferenceTags.jsx'

// The player's own opinions and species trait. Others don't know your
// preferences until you reveal them in conversation.
export default function PlayerProfile() {
  const player = useGameStore((s) => s.state?.player)
  const species = useGameStore((s) => s.species)
  if (!player) return null

  const trait = species?.[player.trait]?.trait

  return (
    <section className="player-profile">
      <h2>You</h2>
      {trait && (
        <p className="player-trait">
          <span className="player-trait-name">{trait.name}</span> — {trait.blurb}
        </p>
      )}
      <PreferenceTags preferences={player.preferences} empty="No strong opinions yet." />
    </section>
  )
}
