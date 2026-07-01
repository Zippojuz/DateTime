import { useEffect } from 'react'
import { useGameStore } from './state/gameStore'
import TitleScreen from './screens/TitleScreen.jsx'
import CreationScreen from './screens/CreationScreen.jsx'
import WorldMap from './screens/WorldMap.jsx'
import DialogueScreen from './screens/DialogueScreen.jsx'

// A minimal screen router driven by the store's `screen` field. A dialogue,
// when active, overlays the play screen.
export default function App() {
  const screen = useGameStore((s) => s.screen)
  const dialogue = useGameStore((s) => s.dialogue)
  const init = useGameStore((s) => s.init)

  useEffect(() => {
    init()
  }, [init])

  if (screen === 'creation') return <CreationScreen />
  if (screen === 'play') {
    return (
      <>
        <WorldMap />
        {dialogue && <DialogueScreen />}
      </>
    )
  }
  return <TitleScreen /> // 'loading' and 'title'
}
