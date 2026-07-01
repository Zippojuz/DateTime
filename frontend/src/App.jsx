import { useEffect } from 'react'
import { useGameStore } from './state/gameStore'
import TitleScreen from './screens/TitleScreen.jsx'
import CreationScreen from './screens/CreationScreen.jsx'
import WorldMap from './screens/WorldMap.jsx'

// Milestone 1: a minimal screen router driven by the store's `screen` field.
// Richer routing (Dialogue, Calendar, Menu) arrives with later milestones.
export default function App() {
  const screen = useGameStore((s) => s.screen)
  const init = useGameStore((s) => s.init)

  useEffect(() => {
    init()
  }, [init])

  if (screen === 'creation') return <CreationScreen />
  if (screen === 'play') return <WorldMap />
  return <TitleScreen /> // 'loading' and 'title'
}
