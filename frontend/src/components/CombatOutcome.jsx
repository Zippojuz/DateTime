import { useGameStore } from '../state/gameStore'

// Post-battle fanfare: victory spoils, a narrow escape, or the Substrate
// spitting you back out — plus Pit outcomes (no spoils, but titles, purses,
// and cred). Rendered at App level so a defeat (which ends the run) still
// gets its moment.
export default function CombatOutcome() {
  const result = useGameStore((s) => s.dungeonResult)
  const clear = useGameStore((s) => s.clearDungeonResult)

  if (result?.type !== 'combat') return null

  const rewards = result.rewards
  const arena = result.arena
  const champ = result.championship

  return (
    <div className="battle-overlay" role="dialog" aria-label="Battle outcome">
      <div className={`outcome-window outcome-window--${result.result}`}>
        {result.result === 'victory' && (
          <>
            <h2 className="outcome-title outcome-title--victory">
              {champ ? 'Champion' : 'Victory'}
            </h2>
            {arena ? (
              <p className="outcome-sub">
                Win #{result.wins} in the Pit. The crowd decides it loves you.
              </p>
            ) : (
              result.enemy && <p className="outcome-sub">{result.enemy} falls.</p>
            )}
            {rewards && (
              <dl className="outcome-rewards">
                <div>
                  <dt>XP</dt>
                  <dd>+{rewards.xp}</dd>
                </div>
                <div>
                  <dt>Credits</dt>
                  <dd>+{rewards.credits} cr</dd>
                </div>
                {rewards.level_ups > 0 && (
                  <div className="outcome-levelup">
                    <dt>Level up!</dt>
                    <dd>
                      {rewards.level_ups > 1 ? `+${rewards.level_ups} levels` : 'Fully restored'}
                    </dd>
                  </div>
                )}
                {rewards.drops?.map((name, i) => (
                  <div key={i}>
                    <dt>Drop</dt>
                    <dd>{name}</dd>
                  </div>
                ))}
              </dl>
            )}
            {arena && (
              <dl className="outcome-rewards">
                {champ && (
                  <div className="outcome-levelup">
                    <dt>Title</dt>
                    <dd>{champ.title}</dd>
                  </div>
                )}
                {champ && (
                  <div>
                    <dt>Purse</dt>
                    <dd>+{champ.purse} cr</dd>
                  </div>
                )}
                {champ?.prize && (
                  <div>
                    <dt>Prize</dt>
                    <dd>{champ.prize}</dd>
                  </div>
                )}
                <div>
                  <dt>Street cred</dt>
                  <dd>
                    +{result.cred_gained} ({result.street_cred})
                  </dd>
                </div>
              </dl>
            )}
            {result.hoard && <p className="outcome-hoard">{result.hoard}</p>}
            {result.unlocked && <p className="outcome-unlocked">♥ {result.unlocked.text}</p>}
          </>
        )}

        {result.result === 'fled' && (
          <>
            <h2 className="outcome-title outcome-title--fled">
              {arena ? 'Forfeit' : 'Got away'}
            </h2>
            <p className="outcome-sub">
              {arena
                ? 'You duck out under the ropes. The crowd boos, then forgets you ever existed.'
                : 'You slip back the way you came, heart hammering.'}
            </p>
          </>
        )}

        {result.result === 'defeat' && (
          <>
            <h2 className="outcome-title outcome-title--defeat">Defeat</h2>
            <p className="outcome-sub">
              {arena
                ? "The Pit takes nothing from the fallen but the win. The ladder waits where you left it."
                : `${result.enemy ? `${result.enemy} stands over you. ` : ''}The Substrate spits you back out into The Shallows.`}
            </p>
            {result.credits_lost > 0 && (
              <p className="outcome-loss">−{result.credits_lost} cr lost in the scramble.</p>
            )}
          </>
        )}

        <button className="btn-primary outcome-continue" onClick={clear} autoFocus>
          Continue
        </button>
      </div>
    </div>
  )
}
