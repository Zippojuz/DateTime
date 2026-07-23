import { useState } from 'react'
import { useGameStore } from '../state/gameStore'
import StatBar from '../components/StatBar.jsx'
import PeoplePanel from '../components/PeoplePanel.jsx'
import PlayerProfile from '../components/PlayerProfile.jsx'
import TravelPanel from '../components/TravelPanel.jsx'
import EncounterCard from '../components/EncounterCard.jsx'
import JobPanel from '../components/JobPanel.jsx'
import GigPanel from '../components/GigPanel.jsx'
import PitView from '../components/PitView.jsx'
import GantryView from '../components/GantryView.jsx'
import StacksView from '../components/StacksView.jsx'
import LyceumView from '../components/LyceumView.jsx'
import HomeView from '../components/HomeView.jsx'
import SteepsView from '../components/SteepsView.jsx'
import TideLineView from '../components/TideLineView.jsx'
import PawnshopView from '../components/PawnshopView.jsx'
import ExchangeView from '../components/ExchangeView.jsx'
import ClinicPanel from '../components/ClinicPanel.jsx'
import DebtPanel from '../components/DebtPanel.jsx'
import EventLog from '../components/EventLog.jsx'
import ShopPanel from '../components/ShopPanel.jsx'
import CyberlinkModal from '../components/CyberlinkModal.jsx'
import GiftPicker from '../components/GiftPicker.jsx'
import GiftReactionCard from '../components/GiftReactionCard.jsx'
import SubstratePanel from '../components/SubstratePanel.jsx'

const DAY_NAMES = ['', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

// The daily loop: check the clock/energy, travel the city, and reach people.
export default function WorldMap() {
  const state = useGameStore((s) => s.state)
  const actions = useGameStore((s) => s.actions)
  const registry = useGameStore((s) => s.attributes)
  const districts = useGameStore((s) => s.districts)
  const venues = useGameStore((s) => s.venues)
  const teahouse = useGameStore((s) => s.teahouse)
  const doAction = useGameStore((s) => s.doAction)
  const openLink = useGameStore((s) => s.openLink)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  const [trainAttr, setTrainAttr] = useState('charm')

  if (!state) return null
  const { player, clock } = state
  const insideVenue = venues?.[player.location]
  const here = districts?.[player.location] ?? insideVenue

  return (
    <main className="world-map">
      <header className="hud">
        <div className="hud-clock">
          <span className="hud-time">{clock.time}</span>
          <span className="hud-date">
            Week {clock.week} · {DAY_NAMES[clock.day] ?? `Day ${clock.day}`}
          </span>
        </div>
        <div className="hud-place">
          <span className="hud-district">
            {here?.name ?? player.location}
            {insideVenue && (
              <span className="hud-under"> · under {districts?.[insideVenue.district]?.name}</span>
            )}
          </span>
          <span className="hud-sub">{player.credits} cr</span>
        </div>
        <div className="hud-identity">
          <strong>{player.identity.name}</strong>
          <span className="hud-sub">
            {player.identity.pronouns} · {player.species}
          </span>
        </div>
        <button className="btn-action hud-link" onClick={openLink} title="Open your Cyberlink">
          ⬡ Link
        </button>
      </header>

      <div className="world-feed">
        <EventLog />
        <EncounterCard />
        <GiftReactionCard />
        <StatBar />
      </div>

      {/* Widescreen: the panels flow into two height-balanced columns so a PC
          screen fills across, not just down. Collapses to one column on
          narrower screens. Which panels show depends on where you are, so a
          masonry flow balances better than a fixed sidebar ever could. */}
      <div className="world-grid">
        <PlayerProfile />

        {here && (
          <section className="placeholder-world">
            <p>{here.vibe}</p>
            {insideVenue?.trait_lines?.[player.trait] && (
              <p className="venue-trait-line">{insideVenue.trait_lines[player.trait]}</p>
            )}
          </section>
        )}

        <TravelPanel />
        <SubstratePanel />
        <JobPanel />
        <GigPanel />
        <PitView />
        <GantryView />
        <StacksView />
        <LyceumView />
        <HomeView />
        <SteepsView />
        <TideLineView />
        <PawnshopView />
        <ExchangeView />
        <ClinicPanel />
        <ShopPanel />
        <PeoplePanel />
        <DebtPanel />

        <section className="action-panel">
        <h2>What do you do?</h2>
        {insideVenue?.training && (
          <p className="venue-perk">{insideVenue.training.blurb}</p>
        )}
        {teahouse?.active && (
          <p className="venue-perk">
            ☕ {teahouse.active.name} — steeping until midnight.
          </p>
        )}
        {error && <p className="form-error">{error}</p>}
        <div className="action-list">
          {Object.entries(actions ?? {}).map(([id, def]) =>
            def.trains ? (
              <div className="action-train" key={id}>
                <select
                  value={trainAttr}
                  onChange={(e) => setTrainAttr(e.target.value)}
                  disabled={busy}
                >
                  {Object.entries(registry ?? {}).map(([attrId, spec]) => (
                    <option key={attrId} value={attrId}>
                      {spec.name}
                    </option>
                  ))}
                </select>
                <button
                  className="btn-action"
                  disabled={busy}
                  onClick={() => doAction('train', trainAttr)}
                >
                  {def.label} ({fmtDuration(def.minutes)})
                </button>
              </div>
            ) : (
              <button
                className="btn-action"
                key={id}
                disabled={busy}
                onClick={() => doAction(id)}
              >
                {def.label} ({fmtDuration(def.minutes)})
              </button>
            ),
          )}
          </div>
        </section>
      </div>

      <GiftPicker />
      <CyberlinkModal />
    </main>
  )
}

function fmtDuration(minutes) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h && m) return `${h}h ${m}m`
  if (h) return `${h}h`
  return `${m}m`
}
