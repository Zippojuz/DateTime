import { useState } from 'react'
import { useGameStore } from '../state/gameStore'

const PRONOUN_PRESETS = ['she/her', 'he/him', 'they/them']

// Character creation. Identity is locked once you begin (see Identity
// Philosophy) — appearance/pronouns/body can change later only through the
// story-gated transformation system. Species offers suggestions from the
// registry but accepts anything: identity is data, never a gate.
export default function CreationScreen() {
  const newGame = useGameStore((s) => s.newGame)
  const speciesRegistry = useGameStore((s) => s.species)
  const busy = useGameStore((s) => s.busy)
  const error = useGameStore((s) => s.error)

  const [name, setName] = useState('')
  const [pronouns, setPronouns] = useState('they/them')
  const [species, setSpecies] = useState('Human')
  const [customTrait, setCustomTrait] = useState('')
  const [appearance, setAppearance] = useState('')
  const [body, setBody] = useState('')

  // A registry species brings its own trait; a custom species picks any (or
  // none). Traits are the mechanical half of a species — chosen here, locked
  // with the rest of your created identity.
  const registryMatch = Object.values(speciesRegistry ?? {}).find(
    (s) => s.name.toLowerCase() === species.trim().toLowerCase(),
  )
  const traitId = registryMatch ? registryMatch.id : customTrait
  const trait = speciesRegistry?.[traitId]?.trait

  const submit = (e) => {
    e.preventDefault()
    if (!name.trim()) return
    newGame({ name, pronouns, species, trait: traitId, appearance, body })
  }

  return (
    <main className="creation-screen">
      <h1 className="creation-title">Who are you?</h1>
      <p className="creation-note">
        Your starting self is locked in. You can change who you become later —
        that&apos;s a story you&apos;ll have to earn.
      </p>

      <form className="creation-form" onSubmit={submit}>
        <label>
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="What do they call you?"
            autoFocus
          />
        </label>

        <label>
          Pronouns
          <div className="pronoun-presets">
            {PRONOUN_PRESETS.map((p) => (
              <button
                type="button"
                key={p}
                className={`chip ${pronouns === p ? 'chip--active' : ''}`}
                onClick={() => setPronouns(p)}
              >
                {p}
              </button>
            ))}
          </div>
          <input
            value={pronouns}
            onChange={(e) => setPronouns(e.target.value)}
            placeholder="Or type your own"
          />
        </label>

        <label>
          Species
          <div className="pronoun-presets species-presets">
            {Object.values(speciesRegistry ?? {}).map((s) => (
              <button
                type="button"
                key={s.id}
                className={`chip ${species === s.name ? 'chip--active' : ''}`}
                title={s.blurb}
                onClick={() => setSpecies(s.name)}
              >
                {s.name}
              </button>
            ))}
          </div>
          <input
            value={species}
            onChange={(e) => setSpecies(e.target.value)}
            placeholder="Or type your own"
          />
          {registryMatch && <span className="species-blurb">{registryMatch.blurb}</span>}
        </label>

        <label>
          Trait
          {!registryMatch && (
            <div className="pronoun-presets trait-presets">
              <button
                type="button"
                className={`chip ${customTrait === '' ? 'chip--active' : ''}`}
                onClick={() => setCustomTrait('')}
              >
                None
              </button>
              {Object.values(speciesRegistry ?? {}).map((s) => (
                <button
                  type="button"
                  key={s.id}
                  className={`chip ${customTrait === s.id ? 'chip--active' : ''}`}
                  title={s.trait?.blurb}
                  onClick={() => setCustomTrait(s.id)}
                >
                  {s.trait?.name}
                </button>
              ))}
            </div>
          )}
          {trait ? (
            <span className="species-blurb">
              <strong className="player-trait-name">{trait.name}</strong> — {trait.blurb}
            </span>
          ) : (
            <span className="species-blurb">
              {registryMatch
                ? 'This species carries no trait.'
                : 'A written-in species may claim any trait — or walk in without one.'}
            </span>
          )}
        </label>

        <label>
          Appearance
          <textarea
            value={appearance}
            onChange={(e) => setAppearance(e.target.value)}
            placeholder="Describe how you look."
            rows={2}
          />
        </label>

        <label>
          Body
          <input
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="However you'd describe it."
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <button className="btn-primary" type="submit" disabled={busy || !name.trim()}>
          {busy ? 'Arriving…' : 'Arrive in Nexus City'}
        </button>
      </form>
    </main>
  )
}
