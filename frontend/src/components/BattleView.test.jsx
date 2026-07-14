import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import BattleView from './BattleView'
import CombatOutcome from './CombatOutcome'
import { useGameStore } from '../state/gameStore'

const COMBAT = {
  active: true,
  turn: 3,
  enemy: {
    id: 'chrome_vixen',
    name: 'Chrome Vixen',
    role: 'normal',
    element: 'kinetic',
    hp: 32,
    description: 'All mirror-finish curves.',
  },
  enemy_hp: 20,
  player_hp: 41,
  charge: 2,
  charge_max: 5,
  guarding: false,
  log: ['Chrome Vixen bars your way.'],
  player_effects: {},
  enemy_effects: {},
  charging: null,
  companion: {
    id: 'vael',
    name: 'Vael',
    role: 'tank',
    element: 'cryo',
    hp: 30,
    max_hp: 42,
    down: false,
  },
}

beforeEach(() => {
  useGameStore.setState({
    busy: false,
    error: null,
    dungeonResult: null,
    items: { stim_tea: { name: 'Stim Tea', type: 'food', description: 'Hot.' } },
    state: { player: { name: 'Kai', inventory: { stim_tea: 2 } } },
    dungeon: {
      combat: COMBAT,
      stats: { level: 5, max_hp: 60 },
      skills: {
        ember_burst: {
          id: 'ember_burst',
          name: 'Ember Burst',
          element: 'thermal',
          cost: 2,
          description: 'A gout of flame.',
        },
      },
    },
  })
})

describe('BattleView', () => {
  it('lays out party, enemy, commands, and party status', () => {
    render(<BattleView />)
    expect(screen.getByRole('dialog', { name: 'Battle' })).toBeInTheDocument()
    // Player and companion on the field + in the status strip.
    expect(screen.getAllByText('Kai').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('Vael').length).toBeGreaterThanOrEqual(2)
    // Enemy header with element badge, and the turn counter.
    expect(screen.getByText('Chrome Vixen')).toBeInTheDocument()
    expect(screen.getByText('Turn 3')).toBeInTheDocument()
    // Command menu.
    expect(screen.getByRole('button', { name: 'Attack' })).toBeEnabled()
    expect(screen.getByRole('button', { name: /Guard/ })).toBeEnabled()
  })

  it('opens the skill submenu and shows cost + element', () => {
    render(<BattleView />)
    fireEvent.click(screen.getByRole('button', { name: /Skill/ }))
    expect(screen.getByRole('button', { name: /Ember Burst/ })).toBeEnabled()
    expect(screen.getByText(/thermal · 2●/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Back/ }))
    expect(screen.getByRole('button', { name: 'Attack' })).toBeInTheDocument()
  })

  it('marks a downed companion instead of an HP bar', () => {
    useGameStore.setState({
      dungeon: {
        ...useGameStore.getState().dungeon,
        combat: { ...COMBAT, companion: { ...COMBAT.companion, down: true, hp: 0 } },
      },
    })
    render(<BattleView />)
    expect(screen.getAllByText('DOWN').length).toBeGreaterThanOrEqual(1)
  })
})

describe('CombatOutcome', () => {
  it('shows the victory fanfare with rewards', () => {
    useGameStore.setState({
      dungeonResult: {
        type: 'combat',
        result: 'victory',
        enemy: 'Chrome Vixen',
        rewards: { xp: 14, credits: 9, level_ups: 1, drops: ['Charge Cell'] },
      },
    })
    render(<CombatOutcome />)
    expect(screen.getByText('Victory')).toBeInTheDocument()
    expect(screen.getByText('+14')).toBeInTheDocument()
    expect(screen.getByText('+9 cr')).toBeInTheDocument()
    expect(screen.getByText('Level up!')).toBeInTheDocument()
    expect(screen.getByText('Charge Cell')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    expect(useGameStore.getState().dungeonResult).toBeNull()
  })

  it('shows the defeat screen with the credit loss', () => {
    useGameStore.setState({
      dungeonResult: {
        type: 'combat',
        result: 'defeat',
        enemy: 'Neon Seraph',
        credits_lost: 12,
      },
    })
    render(<CombatOutcome />)
    expect(screen.getByText('Defeat')).toBeInTheDocument()
    expect(screen.getByText(/−12 cr/)).toBeInTheDocument()
  })

  it('renders nothing for non-combat results', () => {
    useGameStore.setState({ dungeonResult: { type: 'treasure', text: 'Credits!' } })
    const { container } = render(<CombatOutcome />)
    expect(container).toBeEmptyDOMElement()
  })
})
