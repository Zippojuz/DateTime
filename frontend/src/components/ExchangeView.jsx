import { useGameStore } from '../state/gameStore'

// The Triumvirate Exchange — three corps, three storefronts, one atrium
// (and, per a certain buried file, one loading dock). Renders each corp in
// its own voice, under this week's war bulletin.
export default function ExchangeView() {
  const state = useGameStore((s) => s.state)
  const corps = useGameStore((s) => s.corps)

  if (state?.player?.location !== 'triumvirate_exchange' || !corps) return null
  const war = corps.war

  return (
    <section className="exchange-view">
      <h2>The Triumvirate</h2>
      {war && (
        <p className="exchange-war">
          {war.line}
          <span className="exchange-bulletin">{war.bulletin}</span>
        </p>
      )}
      <div className="exchange-grid">
        {Object.values(corps.corps ?? {}).map((corp) => {
          const side = war
            ? war.enemy === corp.id
              ? 'THIS WEEK: THE ENEMY'
              : 'THIS WEEK: ALLIED'
            : ''
          return (
            <article key={corp.id} className={`corp-card corp-card--${corp.id}`}>
              <header className="corp-head">
                <strong>{corp.name}</strong>
                <span className="corp-slogan">{corp.slogan}</span>
              </header>
              <p className="corp-sector">{corp.sector}</p>
              <p className="corp-blurb">{corp.blurb}</p>
              <p className="corp-voice">{corp.voice}</p>
              {side && <p className="corp-side">{side}</p>}
              <p className="corp-denial">{corp.denial}</p>
            </article>
          )
        })}
      </div>
    </section>
  )
}
