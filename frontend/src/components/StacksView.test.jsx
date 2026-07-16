import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StacksView from './StacksView'
import { useGameStore } from '../state/gameStore'

const STACKS = {
  venue: 'the_stacks',
  minutes: 90,
  energy: -10,
  researched_today: false,
  draft: {
    subject: 'the_draft',
    label: 'The draft in row nine',
    blurb: "Forty years of tickets closed 'no fault found'.",
  },
}

function seed(over = {}) {
  useGameStore.setState({
    busy: false,
    state: { player: { location: 'the_stacks' } },
    stacks: STACKS,
    characters: [
      { id: 'oona', name: 'Oona', met: true },
      { id: 'vex', name: 'Mama Vex', met: false },
    ],
    lastResearch: null,
    ...over,
  })
}

describe('StacksView', () => {
  beforeEach(() => seed())

  it('renders nothing outside the archive', () => {
    seed({ state: { player: { location: 'citadel_ring' } } })
    const { container } = render(<StacksView />)
    expect(container).toBeEmptyDOMElement()
  })

  it('offers the draft and files on people you have met — only', () => {
    const researchFile = vi.fn()
    useGameStore.setState({ researchFile })
    render(<StacksView />)
    expect(screen.getByText('The draft in row nine')).toBeInTheDocument()
    expect(screen.getByText('Oona')).toBeInTheDocument()
    expect(screen.queryByText('Mama Vex')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Pull the file · 1h 30m' }))
    expect(researchFile).toHaveBeenCalledWith('the_draft')
  })

  it('closes the desk after the daily pull and shows the result', () => {
    seed({
      stacks: { ...STACKS, researched_today: true },
      lastResearch: { text: 'The air is reading over your shoulder.' },
    })
    render(<StacksView />)
    expect(screen.getByText(/reading over your shoulder/)).toBeInTheDocument()
    expect(screen.getByText(/There is no desk clerk/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Pull/ })).not.toBeInTheDocument()
  })

  it('hides the draft once Index is perceived', () => {
    seed({ stacks: { ...STACKS, draft: null } })
    render(<StacksView />)
    expect(screen.queryByText(/row nine/)).not.toBeInTheDocument()
    expect(screen.getByText('Oona')).toBeInTheDocument()
  })
})
