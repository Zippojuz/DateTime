import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DateScreen from './DateScreen'
import { useGameStore } from '../state/gameStore'

const BEAT = {
  npc: 'oona',
  npc_name: 'Oona',
  venue: 'the_steeps',
  title: 'A soak at the Steeps',
  beat: 0,
  total_beats: 3,
  opening: 'Okay, this was a good call.',
  text: 'The first terrace is body-warm and green-lit.',
  choices: [
    { index: 0, text: 'Settle in beside them.' },
    { index: 1, text: 'Cannonball.' },
  ],
  gained: 0,
  done: false,
}

function seed(over = {}) {
  useGameStore.setState({ busy: false, error: null, date: BEAT, ...over })
}

describe('DateScreen', () => {
  beforeEach(() => seed())

  it('renders nothing when nobody said yes', () => {
    seed({ date: null })
    const { container } = render(<DateScreen />)
    expect(container).toBeEmptyDOMElement()
  })

  it('plays a beat: opening, scene text, and the choices', () => {
    const chooseDateBeat = vi.fn()
    useGameStore.setState({ chooseDateBeat })
    render(<DateScreen />)
    expect(screen.getByText('A soak at the Steeps')).toBeInTheDocument()
    expect(screen.getByText(/good call/)).toBeInTheDocument()
    expect(screen.getByText('1 / 3')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cannonball.' }))
    expect(chooseDateBeat).toHaveBeenCalledWith(1)
  })

  it('shows the closing verdict and heads home', () => {
    const closeDate = vi.fn()
    useGameStore.setState({ closeDate })
    seed({
      date: {
        ...BEAT,
        done: true,
        good: true,
        gained: 14,
        closing: 'Next time, she says.',
        reply: 'She does not let go of your hand.',
      },
    })
    render(<DateScreen />)
    expect(screen.getByText(/Next time/)).toBeInTheDocument()
    expect(screen.getByText(/It went well.*\+14 ♥/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Head home' }))
    expect(closeDate).toHaveBeenCalled()
  })

  it('lets you walk out mid-scene', () => {
    const leaveDate = vi.fn()
    useGameStore.setState({ leaveDate })
    render(<DateScreen />)
    fireEvent.click(screen.getByRole('button', { name: 'Leave the date' }))
    expect(leaveDate).toHaveBeenCalled()
  })
})
