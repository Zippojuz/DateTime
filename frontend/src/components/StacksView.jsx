import { useGameStore } from '../state/gameStore'

// The Stacks — the Citadel Ring's archive. The research desk: one pull a day.
// Files on people you've met reveal a preference (marked, unlike gossip);
// and one file isn't about a person at all — the draft in row nine.
export default function StacksView() {
  const state = useGameStore((s) => s.state)
  const stacks = useGameStore((s) => s.stacks)
  const characters = useGameStore((s) => s.characters)
  const lastResearch = useGameStore((s) => s.lastResearch)
  const researchFile = useGameStore((s) => s.researchFile)
  const busy = useGameStore((s) => s.busy)

  if (state?.player?.location !== 'the_stacks' || !stacks) return null

  const met = characters.filter((c) => c.met)
  const cost = `${Math.floor(stacks.minutes / 60)}h${stacks.minutes % 60 ? ` ${stacks.minutes % 60}m` : ''}`

  return (
    <section className="stacks-view">
      <h2>The Stacks</h2>

      <h3>Research desk</h3>
      {lastResearch && <p className="research-result">{lastResearch.text}</p>}
      {stacks.researched_today ? (
        <p className="research-closed">
          One pull a day. The desk clerk taps the sign. There is no desk clerk.
        </p>
      ) : (
        <ul className="research-list">
          {stacks.draft && (
            <li className="research-item research-item--draft">
              <div className="research-info">
                <span className="research-name">{stacks.draft.label}</span>
                <span className="research-sub">{stacks.draft.blurb}</span>
              </div>
              <button
                className="btn-action"
                disabled={busy}
                onClick={() => researchFile(stacks.draft.subject)}
              >
                Pull the file · {cost}
              </button>
            </li>
          )}
          {met.map((c) => (
            <li key={c.id} className="research-item">
              <div className="research-info">
                <span className="research-name">{c.name}</span>
                <span className="research-sub">
                  What does the archive know that you don&apos;t?
                </span>
              </div>
              <button
                className="btn-action"
                disabled={busy}
                onClick={() => researchFile(c.id)}
              >
                Pull their file · {cost}
              </button>
            </li>
          ))}
          {!stacks.draft && met.length === 0 && (
            <li className="research-item">
              <span className="research-sub">
                The archive files people under who they are to you. Go meet someone.
              </span>
            </li>
          )}
        </ul>
      )}
    </section>
  )
}
