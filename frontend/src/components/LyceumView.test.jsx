import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LyceumView from './LyceumView'
import { useGameStore } from '../state/gameStore'

const LYCEUM = {
  venue: 'the_lyceum',
  is_library: false,
  already_classed_today: false,
  courses: [
    {
      id: 'rhet_101',
      code: 'RHET 101',
      name: 'First Impressions',
      dept: 'Rhetoric & Presence',
      stat: 'charm',
      tier: 100,
      grants: 2,
      tuition: 0,
      minutes: 60,
      energy: -8,
      sessions: 1,
      blurb: 'The first four seconds.',
      perk: null,
      state: 'available',
    },
    {
      id: 'rhet_301',
      code: 'RHET 301',
      name: 'Command of the Room',
      dept: 'Rhetoric & Presence',
      stat: 'charm',
      tier: 300,
      grants: 4,
      tuition: 90,
      minutes: 90,
      energy: -12,
      sessions: 3,
      blurb: 'Walk in and the room reorganizes.',
      perk: { name: 'Silver Tongue', blurb: 'People warm faster.' },
      state: 'locked',
      reasons: ['Requires RHET 201 (The Long Con of Being Liked)', 'Requires Charm 12 (you have 5)'],
    },
  ],
  transcript: [],
  enrollment: null,
  quests: [
    {
      id: 'founders_library',
      name: "The Founder's Library",
      brief: 'Four volumes, scattered.',
      state: 'ready',
      have: 4,
      need: 4,
    },
  ],
  readable: [{ id: 'primer_lace', name: 'Cold Boot: A Field Manual', hint: '+1 Hacking', qty: 1 }],
}

function seed(over = {}) {
  useGameStore.setState({
    busy: false,
    state: { player: { location: 'the_lyceum' } },
    lyceum: LYCEUM,
    lastClass: null,
    lastRead: null,
    ...over,
  })
}

describe('LyceumView', () => {
  beforeEach(() => seed())

  it('renders nothing away from the college or reading rooms', () => {
    seed({ state: { player: { location: 'the_pit' } } })
    const { container } = render(<LyceumView />)
    expect(container).toBeEmptyDOMElement()
  })

  it('enrolls in an available course', () => {
    const attendClass = vi.fn()
    useGameStore.setState({ attendClass })
    render(<LyceumView />)
    expect(screen.getByText('First Impressions')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Sit in' }))
    expect(attendClass).toHaveBeenCalledWith('rhet_101')
  })

  it('shows a locked course with its reasons and the perk it would grant', () => {
    render(<LyceumView />)
    expect(screen.getByText(/Requires Charm 12/)).toBeInTheDocument()
    expect(screen.getByText('Perk: Silver Tongue')).toBeInTheDocument()
  })

  it('reads a book from the pack', () => {
    const readBook = vi.fn()
    useGameStore.setState({ readBook })
    render(<LyceumView />)
    fireEvent.click(screen.getByRole('button', { name: 'Read · +1 Hacking' }))
    expect(readBook).toHaveBeenCalledWith('primer_lace')
  })

  it('hands in a completed collectible set', () => {
    const turnInQuest = vi.fn()
    useGameStore.setState({ turnInQuest })
    render(<LyceumView />)
    fireEvent.click(screen.getByRole('button', { name: 'Hand them over' }))
    expect(turnInQuest).toHaveBeenCalledWith('founders_library')
  })
})
