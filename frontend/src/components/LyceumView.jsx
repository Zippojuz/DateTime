import { useGameStore } from '../state/gameStore'

// The Lyceum & the library's reading rooms. Courses are a gated ladder
// (100->400): the free 100s in the Stacks, the whole thing at the Lyceum.
// One class a day; 300/400 run as terms across several days. Also readable
// books and the professor's quest board.
export default function LyceumView() {
  const state = useGameStore((s) => s.state)
  const lyceum = useGameStore((s) => s.lyceum)
  const lastClass = useGameStore((s) => s.lastClass)
  const lastRead = useGameStore((s) => s.lastRead)
  const lastBrowse = useGameStore((s) => s.lastBrowse)
  const attendClass = useGameStore((s) => s.attendClass)
  const readBook = useGameStore((s) => s.readBook)
  const browseShelves = useGameStore((s) => s.browseShelves)
  const turnInQuest = useGameStore((s) => s.turnInQuest)
  const clearClassNews = useGameStore((s) => s.clearClassNews)
  const busy = useGameStore((s) => s.busy)

  const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s)

  const loc = state?.player?.location
  if ((loc !== 'the_lyceum' && loc !== 'the_stacks') || !lyceum) return null

  const title = lyceum.is_library ? 'The Reading Rooms' : 'The Lyceum'
  const term = lyceum.enrollment

  return (
    <section className="lyceum-view">
      <h2>{title}</h2>
      {lyceum.is_library && (
        <p className="lyceum-sub">
          The Stacks&apos; public reading rooms — the hundred level of anything, free. The rest is
          taught up at the Lyceum.
        </p>
      )}

      {(lastClass || lastRead || lastBrowse) && (
        <div className="lyceum-news" onClick={clearClassNews}>
          {lastRead?.lore && (
            <div className="lore-passage">
              <span className="lore-title">{lastRead.lore.title}</span>
              <p className="lore-text">{lastRead.lore.text}</p>
            </div>
          )}
          {lastRead?.outcome && (
            <p>
              You read <strong>{lastRead.item}</strong>.{' '}
              {lastRead.outcome.stat
                ? `${cap(lastRead.outcome.stat)} is now ${lastRead.outcome.now}.`
                : `You can run ${lastRead.outcome.name} now.`}
            </p>
          )}
          {lastBrowse && (
            <p>
              {lastBrowse.found
                ? `Something on the shelf finds you: ${lastBrowse.found.name}.`
                : lastBrowse.text}
            </p>
          )}
          {lastClass?.turnIn && (
            <p>
              {lastClass.turnIn.text}
              {lastClass.turnIn.reward_credits > 0 &&
                ` (+${lastClass.turnIn.reward_credits} cr)`}
            </p>
          )}
          {lastClass && !lastClass.turnIn && (
            <p>
              {lastClass.completed ? (
                <>
                  <strong>{lastClass.course}</strong> — credit earned.
                  {lastClass.gained &&
                    ` ${lastClass.gained.stat[0].toUpperCase()}${lastClass.gained.stat.slice(1)} +${lastClass.gained.amount} (now ${lastClass.gained.now}).`}
                  {lastClass.perk && ` Perk unlocked: ${lastClass.perk.name} — ${lastClass.perk.blurb}`}
                </>
              ) : (
                <>
                  <strong>{lastClass.course}</strong> — session {lastClass.sessions_done} of{' '}
                  {lastClass.sessions}. Come back tomorrow.
                </>
              )}
            </p>
          )}
        </div>
      )}

      {term && (
        <p className="lyceum-term">
          Enrolled: <strong>{term.code}</strong> {term.name} — session {term.sessions_done}/
          {term.sessions}.
        </p>
      )}
      {lyceum.already_classed_today && (
        <p className="lyceum-closed">One class a day. Your brain has a bandwidth, and you&apos;ve spent it.</p>
      )}

      <ul className="course-list">
        {lyceum.courses.map((c) => (
          <li key={c.id} className={`course course--${c.state} course--t${c.tier}`}>
            <div className="course-info">
              <span className="course-head">
                <span className="course-code">{c.code}</span> {c.name}
              </span>
              <span className="course-sub">{c.blurb}</span>
              <span className="course-meta">
                {c.stat && (
                  <span className="course-tag">
                    +{c.grants} {c.stat}
                  </span>
                )}
                {c.tuition > 0 && <span className="course-tag">{c.tuition} cr</span>}
                {c.sessions > 1 && <span className="course-tag">{c.sessions}-session term</span>}
                {c.perk && <span className="course-tag course-tag--perk">Perk: {c.perk.name}</span>}
              </span>
              {c.state === 'locked' && c.reasons && (
                <span className="course-locked">{c.reasons.join(' · ')}</span>
              )}
            </div>
            <div className="course-action">
              {c.state === 'completed' && <span className="course-done">✓ Completed</span>}
              {c.state === 'in_progress' && (
                <button className="btn-action" disabled={busy} onClick={() => attendClass(c.id)}>
                  Attend ({c.sessions_done + 1}/{c.sessions})
                </button>
              )}
              {c.state === 'available' && (
                <button className="btn-primary" disabled={busy} onClick={() => attendClass(c.id)}>
                  {c.sessions > 1 ? 'Begin the term' : c.tuition > 0 ? 'Enroll' : 'Sit in'}
                </button>
              )}
              {c.state === 'locked' && <span className="course-lock">🔒</span>}
            </div>
          </li>
        ))}
      </ul>

      {lyceum.can_browse && (
        <div className="shelf-browse">
          <button
            className="btn-action"
            disabled={busy || lyceum.browsed_today}
            onClick={browseShelves}
          >
            {lyceum.browsed_today ? "You've browsed today" : 'Browse the shelves'}
          </button>
          <span className="shelf-hint">A book turns up now and then — some only shelved here.</span>
        </div>
      )}

      {lyceum.readable?.length > 0 && (
        <>
          <h3>Read from your pack</h3>
          <ul className="book-list">
            {lyceum.readable.map((b) => (
              <li key={b.id} className={`book-row book-row--${b.kind}${b.locked ? ' book-row--locked' : ''}`}>
                <span className="book-name">
                  {b.kind === 'lore' && <span className="book-kind">lore</span>}
                  {b.name}
                  {b.qty > 1 && ` ×${b.qty}`}
                  {b.locked && <span className="book-gate"> — {b.reason}</span>}
                  {b.kind === 'lore' && b.known && <span className="book-read"> ✓ read</span>}
                </span>
                <button
                  className="btn-action"
                  disabled={busy || b.locked}
                  onClick={() => readBook(b.id)}
                >
                  {b.kind === 'lore' ? (b.known ? 'Re-read' : 'Read') : `Read · ${b.hint}`}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {!lyceum.is_library && lyceum.quests?.length > 0 && (
        <>
          <h3>Professor Halloran&apos;s desk</h3>
          <ul className="quest-list">
            {lyceum.quests.map((q) => (
              <li key={q.id} className={`quest quest--${q.state}`}>
                <div className="quest-info">
                  <span className="quest-name">{q.name}</span>
                  <span className="quest-brief">{q.brief}</span>
                  {q.need > 0 && (
                    <span className="quest-progress">
                      {q.have}/{q.need} volumes
                    </span>
                  )}
                </div>
                {q.state === 'ready' && (
                  <button className="btn-primary" disabled={busy} onClick={() => turnInQuest(q.id)}>
                    Hand them over
                  </button>
                )}
                {q.state === 'done' && <span className="course-done">✓ Done</span>}
              </li>
            ))}
          </ul>
        </>
      )}

      {lyceum.transcript?.length > 0 && (
        <details className="transcript">
          <summary>Transcript ({lyceum.transcript.length})</summary>
          <ul>
            {lyceum.transcript.map((t) => (
              <li key={t.code}>
                <span className="course-code">{t.code}</span> {t.name}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
