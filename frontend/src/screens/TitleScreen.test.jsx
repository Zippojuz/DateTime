import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import TitleScreen from './TitleScreen'
import { useGameStore } from '../state/gameStore'

beforeEach(() => {
  // Reset to a connected 'title' state without a save.
  useGameStore.setState({
    connection: 'ok',
    connectionError: null,
    screen: 'title',
    hasSave: false,
  })
})

describe('TitleScreen', () => {
  it('renders the logo and tagline', () => {
    render(<TitleScreen />)
    expect(screen.getByText('NEXUS CITY')).toBeInTheDocument()
    expect(screen.getByText(/never sleeps/)).toBeInTheDocument()
  })

  it('shows the connected status and an enabled New Game button', () => {
    render(<TitleScreen />)
    expect(screen.getByText(/Connected to Nexus core/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'New Game' })).toBeEnabled()
  })

  it('offers Continue only when a save exists', () => {
    const { unmount } = render(<TitleScreen />)
    expect(screen.queryByRole('button', { name: 'Continue' })).toBeNull()
    unmount()

    // Flip state while nothing is mounted, then render fresh.
    useGameStore.setState({ hasSave: true })
    render(<TitleScreen />)
    expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument()
  })
})
