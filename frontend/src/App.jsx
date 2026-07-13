import { useEffect } from 'react'
import { useGameStore } from './state/gameStore'
import TitleScreen from './screens/TitleScreen.jsx'
import CreationScreen from './screens/CreationScreen.jsx'
import WorldMap from './screens/WorldMap.jsx'
import DialogueScreen from './screens/DialogueScreen.jsx'
import DungeonScreen from './screens/DungeonScreen.jsx'

// A minimal screen router driven by the store's `screen` field. A dialogue,
// when active, overlays the play screen; an active Substrate run replaces it.
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
    if (inDungeon) return <DungeonScreen />
    return (
      <>
        <WorldMap />
        {dialogue && <DialogueScreen />}
      </>
    )
  }
  return <TitleScreen /> // 'loading' and 'title'
}
