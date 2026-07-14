import { useGameStore } from '../state/gameStore'

// Work available in your current district. Pay is base + a bonus from the job's
// stat, so it shows "pays N+ cr".
export default function JobPanel() {
  const jobs = useGameStore((s) => s.jobs)
  const workJob = useGameStore((s) => s.workJob)
  const busy = useGameStore((s) => s.busy)
  const lastJob = useGameStore((s) => s.lastJob)

  if (!jobs.length) return null
  const here = jobs.filter((j) => j.reachable)

  return (
    <section className="job-panel">
      <h2>Work</h2>
      {lastJob && (
        <p className="job-result">
          Earned {lastJob.pay} cr from {lastJob.job}.
          {lastJob.tip > 0 && ` A lucky tip landed in there (+${lastJob.tip} cr).`}
        </p>
      )}
      {here.length === 0 ? (
        <p className="job-none">No work here right now — try another district.</p>
      ) : (
        <ul className="job-list">
          {here.map((j) => (
            <li key={j.id} className="job">
              <div className="job-info">
                <strong>{j.name}</strong>
                <span className="job-sub">{j.description}</span>
                <span className="job-meta">
                  {fmtDuration(j.minutes)} · {j.energy} energy · pays {j.pay}+ cr
                </span>
              </div>
              <button className="btn-action" disabled={busy} onClick={() => workJob(j.id)}>
                Work
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function fmtDuration(minutes) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h && m) return `${h}h ${m}m`
  if (h) return `${h}h`
  return `${m}m`
}
