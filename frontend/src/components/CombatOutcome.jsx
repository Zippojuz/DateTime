import { useGameStore } from '../state/gameStore'

// Post-battle fanfare: victory spoils, a narrow escape, or the Substrate
// spitting you back out. Rendered at App level so a defeat (which ends the
// run) still gets its moment.
export default function CombatOutcome() {
  const result = useGameStore((s) => s.dungeonResult)
  const clear = useGameStore((s) => s.clearDungeonResult)

  if (result?.type !== 'combat') return null

  const rewards = result.rewards

  return (
    <div className="battle-overlay" role="dialog" aria-label="Battle outcome">
      <div className={`outcome-window outcome-window--${result.result}`}>
        {result.result === 'victory' && (
          <>
            <h2 className="outcome-title outcome-title--victory">Victory</h2>
            {result.enemy && <p className="outcome-sub">{result.enemy} falls.</p>}
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
            {result.hoard && <p className="outcome-hoard">{result.hoard}</p>}
          </>
        )}

        {result.result === 'fled' && (
          <>
            <h2 className="outcome-title outcome-title--fled">Got away</h2>
            <p className="outcome-sub">You slip back the way you came, heart hammering.</p>
          </>
        )}

        {result.result === 'defeat' && (
          <>
            <h2 className="outcome-title outcome-title--defeat">Defeat</h2>
            <p className="outcome-sub">
              {result.enemy ? `${result.enemy} stands over you. ` : ''}
              The Substrate spits you back out into The Shallows.
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
