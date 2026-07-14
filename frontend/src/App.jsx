import { useEffect } from 'react'
import { useGameStore } from './state/gameStore'
import TitleScreen from './screens/TitleScreen.jsx'
import CreationScreen from './screens/CreationScreen.jsx'
import WorldMap from './screens/WorldMap.jsx'
import DialogueScreen from './screens/DialogueScreen.jsx'
import DungeonScreen from './screens/DungeonScreen.jsx'
import CombatOutcome from './components/CombatOutcome.jsx'

// A minimal screen router driven by the store's `screen` field. A dialogue,
// when active, overlays the play screen; an active Substrate run replaces it.
// The combat outcome modal sits above whichever is showing — a defeat ends
// the run, dropping back to the world map, and still needs its moment.
export default function App() {
  const screen = useGameStore((s) => s.screen)
  const dialogue = useGameStore((s) => s.dialogue)
  const inDungeon = useGameStore((s) => Boolean(s.dungeon?.run))
  const init = useGameStore((s) => s.init)

  useEffect(() => {
    init()
  }, [init])

  if (screen === 'creation') return <CreationScreen />
  if (screen === 'play') {
    return (
      <>
        {inDungeon ? (
          <DungeonScreen />
        ) : (
          <>
            <WorldMap />
            {dialogue && <DialogueScreen />}
          </>
        )}
        <CombatOutcome />
      </>
    )
  }
  return <TitleScreen /> // 'loading' and 'title'
}
