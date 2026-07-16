import { useEffect } from 'react'
import { useGameStore } from './state/gameStore'
import TitleScreen from './screens/TitleScreen.jsx'
import LoginScreen from './screens/LoginScreen.jsx'
import AdminScreen from './screens/AdminScreen.jsx'
import CreationScreen from './screens/CreationScreen.jsx'
import WorldMap from './screens/WorldMap.jsx'
import DialogueScreen from './screens/DialogueScreen.jsx'
import DateScreen from './components/DateScreen.jsx'
import AskOutPicker from './components/AskOutPicker.jsx'
import DungeonScreen from './screens/DungeonScreen.jsx'
import CombatOutcome from './components/CombatOutcome.jsx'
import BattleView from './components/BattleView.jsx'

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

  if (screen === 'login') return <LoginScreen />
  if (screen === 'admin') return <AdminScreen />
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
            <AskOutPicker />
            <DateScreen />
            {/* Arena bouts happen without a Substrate run — the battle modal
                rides over the world map (it renders null unless a fight is on). */}
            <BattleView />
          </>
        )}
        <CombatOutcome />
      </>
    )
  }
  return <TitleScreen /> // 'loading' and 'title'
}
