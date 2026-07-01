import { useGameStore } from '../state/gameStore'

// Overlay conversation view. Shows the current node text and choices; locked
// choices display their requirement. Closes when the conversation ends.
export default function DialogueScreen() {
  const dialogue = useGameStore((s) => s.dialogue)
  const chooseDialogue = useGameStore((s) => s.chooseDialogue)
  const closeDialogue = useGameStore((s) => s.closeDialogue)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  if (!dialogue) return null
  const { npcName, node, lastGained } = dialogue

  return (
    <div className="dialogue-overlay" role="dialog" aria-label={`Talking with ${npcName}`}>
      <div className="dialogue-box">
        <header className="dialogue-header">
          <span className="dialogue-npc">{npcName}</span>
          {lastGained > 0 && <span className="dialogue-affection">+{lastGained} ♥</span>}
          <button className="dialogue-close" onClick={closeDialogue} aria-label="Leave">
            ✕
          </button>
        </header>

        <p className="dialogue-text">{node.text}</p>

        {error && <p className="form-error">{error}</p>}

        <ul className="dialogue-choices">
          {node.choices.map((choice) => (
            <li key={choice.index}>
              <button
                className="dialogue-choice"
                disabled={choice.locked || busy}
                onClick={() => chooseDialogue(choice.index)}
              >
                {choice.text}
                {choice.locked && choice.requires && (
                  <span className="choice-lock">
                    {' '}
                    (needs {formatRequires(choice.requires)})
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function formatRequires(requires) {
  return Object.entries(requires)
    .map(([attr, value]) => `${attr} ${value}`)
    .join(', ')
}
