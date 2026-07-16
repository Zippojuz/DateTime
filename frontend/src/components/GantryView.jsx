import { useGameStore } from '../state/gameStore'

// Gantry 9 — the rooftop-line terminus teahouse. Two things happen up here:
// tea service (one cup a day, its effect rides until midnight) and the
// Lookout, the almanac board of the whole city composed by the server.
export default function GantryView() {
  const state = useGameStore((s) => s.state)
  const teahouse = useGameStore((s) => s.teahouse)
  const lookout = useGameStore((s) => s.lookout)
  const lastPour = useGameStore((s) => s.lastPour)
  const sipTea = useGameStore((s) => s.sipTea)
  const busy = useGameStore((s) => s.busy)

  if (state?.player?.location !== 'gantry_9' || !teahouse) return null

  return (
    <section className="gantry-view">
      <h2>Gantry 9</h2>

      <div className="tea-service">
        <h3>Tea service</h3>
        {teahouse.active ? (
          <p className="tea-active">
            ☕ <strong>{teahouse.active.name}</strong> is steeping through you —{' '}
            {teahouse.active.blurb}
          </p>
        ) : teahouse.sipped_today ? (
          <p className="tea-active">One cup a day. The chalkboard is very firm about this.</p>
        ) : (
          <ul className="tea-menu">
            {Object.entries(teahouse.menu).map(([id, tea]) => (
              <li key={id} className="tea-item">
                <div className="tea-info">
                  <span className="tea-name">{tea.name}</span>
                  <span className="tea-blurb">{tea.blurb}</span>
                </div>
                <button className="btn-action" disabled={busy} onClick={() => sipTea(id)}>
                  Pour · {teahouse.minutes}m · {tea.cost}cr
                </button>
              </li>
            ))}
          </ul>
        )}
        {lastPour && <p className="tea-pour-line">{lastPour.line}</p>}
      </div>

      {lookout && (
        <div className="lookout">
          <h3>The Lookout</h3>
          <p className="lookout-sub">
            The city from nine floors up — week {lookout.week}, {lookout.time}.
          </p>
          <div className="lookout-board">
            <div className="lookout-col">
              <h4>People</h4>
              <ul className="lookout-list">
                {lookout.people.map((p) => (
                  <li
                    key={p.id}
                    className={`lookout-row${p.available ? '' : ' lookout-row--off'}`}
                  >
                    <strong>{p.name}</strong>
                    <span>
                      {p.place} · {p.activity}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="lookout-col">
              <h4>Lights on</h4>
              <ul className="lookout-list">
                {lookout.venues.map((v) => (
                  <li key={v.id} className={`lookout-row${v.open ? '' : ' lookout-row--off'}`}>
                    <strong>{v.name}</strong>
                    <span>
                      {v.district} · {v.hours} · {v.open ? 'open' : 'closed'}
                    </span>
                  </li>
                ))}
              </ul>
              <h4>Today</h4>
              <ul className="lookout-list">
                <li className="lookout-row">
                  <strong>Vex's board</strong>
                  <span>
                    {lookout.gig.name} — {lookout.gig.brief}
                  </span>
                </li>
                <li className="lookout-row">
                  <strong>The Pit card</strong>
                  <span>
                    Fight #{lookout.pit.next_number} vs {lookout.pit.next_enemy}
                    {lookout.pit.next_title ? ` — ${lookout.pit.next_title}` : ''}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
