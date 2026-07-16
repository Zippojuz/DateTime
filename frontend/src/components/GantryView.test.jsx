import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import GantryView from './GantryView'
import { useGameStore } from '../state/gameStore'

const TEAHOUSE = {
  venue: 'gantry_9',
  minutes: 20,
  energy: 5,
  menu: {
    kettle_lightning: {
      name: 'Kettle Lightning',
      cost: 14,
      blurb: 'Walks take half as long today.',
    },
  },
  active: null,
  sipped_today: false,
}

const LOOKOUT = {
  time: '08:25',
  week: 1,
  day: 1,
  people: [{ id: 'oona', name: 'Oona', place: 'The Hold', activity: 'Morning coaching', available: true }],
  venues: [{ id: 'the_pit', name: 'The Pit', district: 'The Grid', open: false, hours: '16:00–04:00' }],
  gig: { id: 'g1', name: 'Cold Handoff', brief: 'A package. No questions.' },
  pit: { wins: 0, next_number: 1, next_enemy: 'Scrapper', next_title: null },
}

function seed(over = {}) {
  useGameStore.setState({
    busy: false,
    state: { player: { location: 'gantry_9' } },
    teahouse: TEAHOUSE,
    lookout: LOOKOUT,
    lastPour: null,
    ...over,
  })
}

describe('GantryView', () => {
  beforeEach(() => seed())

  it('renders nothing away from the gantry', () => {
    seed({ state: { player: { location: 'the_grid' } } })
    const { container } = render(<GantryView />)
    expect(container).toBeEmptyDOMElement()
  })

  it('pours from the chalkboard menu', () => {
    const sipTea = vi.fn()
    useGameStore.setState({ sipTea })
    render(<GantryView />)
    fireEvent.click(screen.getByRole('button', { name: /Pour · 20m · 14cr/ }))
    expect(sipTea).toHaveBeenCalledWith('kettle_lightning')
  })

  it('shows what is steeping instead of the menu', () => {
    seed({
      teahouse: {
        ...TEAHOUSE,
        active: { id: 'kettle_lightning', ...TEAHOUSE.menu.kettle_lightning },
        sipped_today: true,
      },
    })
    render(<GantryView />)
    expect(screen.getByText(/steeping through you/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Pour/ })).not.toBeInTheDocument()
  })

  it('hangs the Lookout board with people, lights, and the day sheet', () => {
    render(<GantryView />)
    expect(screen.getByText('Oona')).toBeInTheDocument()
    expect(screen.getByText(/The Hold · Morning coaching/)).toBeInTheDocument()
    expect(screen.getByText(/16:00–04:00 · closed/)).toBeInTheDocument()
    expect(screen.getByText(/Cold Handoff/)).toBeInTheDocument()
    expect(screen.getByText(/Fight #1 vs Scrapper/)).toBeInTheDocument()
  })
})
