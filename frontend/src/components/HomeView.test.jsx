import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import HomeView from './HomeView'
import { useGameStore } from '../state/gameStore'

const BOARD = {
  current: 'berth',
  current_name: 'Your Docking Berth',
  at_home: false,
  homes: [
    {
      id: 'berth',
      name: 'Your Docking Berth',
      district: 'docking_quarter',
      tier: 0,
      rent: 0,
      price: 0,
      rest_minutes: 540,
      stash: 0,
      host: false,
      perk: {},
      vibe: 'The fold-down bunk in your docked ship.',
      current: true,
      owned: true,
      can_rent: false,
      can_buy: false,
    },
    {
      id: 'tide_houseboat',
      name: 'The Salt Wren (houseboat)',
      district: 'docking_quarter',
      tier: 2,
      rent: 55,
      price: 1100,
      rest_minutes: 450,
      stash: 12,
      host: true,
      perk: { luck_bonus: 1 },
      vibe: 'A patched-hull houseboat.',
      current: false,
      owned: false,
      can_rent: true,
      can_buy: false,
    },
  ],
}

function seed(over = {}) {
  useGameStore.setState({
    busy: false,
    homes: BOARD,
    state: { player: { stash: {}, inventory: {} } },
    districts: { docking_quarter: { name: 'Docking Quarter' } },
    lastHomeEvent: null,
    ...over,
  })
}

describe('HomeView', () => {
  beforeEach(() => seed())

  it('names your current residence and its listings', () => {
    render(<HomeView />)
    // Named in the current-residence line and again in the listings.
    expect(screen.getAllByText('Your Docking Berth').length).toBeGreaterThan(0)
    expect(screen.getByText('The Salt Wren (houseboat)')).toBeInTheDocument()
    // A rentable place offers a rent button at its weekly rate.
    expect(screen.getByText(/Rent 55\/wk/)).toBeInTheDocument()
  })

  it('tells you to go home to sleep when you are away', () => {
    render(<HomeView />)
    expect(screen.getByText(/Go home to sleep/)).toBeInTheDocument()
  })

  it('offers a full night when you are home', () => {
    seed({ homes: { ...BOARD, at_home: true } })
    render(<HomeView />)
    expect(screen.getByText(/full night's sleep/)).toBeInTheDocument()
  })
})
