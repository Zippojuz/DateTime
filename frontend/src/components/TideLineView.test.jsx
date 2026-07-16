import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TideLineView from './TideLineView'
import { useGameStore } from '../state/gameStore'

function seed(over = {}) {
  useGameStore.setState({
    busy: false,
    state: { player: { location: 'the_tide_line' } },
    lastSalvage: null,
    ...over,
  })
}

describe('TideLineView', () => {
  beforeEach(() => seed())

  it('renders nothing above the water line', () => {
    seed({ state: { player: { location: 'docking_quarter' } } })
    const { container } = render(<TideLineView />)
    expect(container).toBeEmptyDOMElement()
  })

  it('wades in', () => {
    const wadeIn = vi.fn()
    useGameStore.setState({ wadeIn })
    render(<TideLineView />)
    fireEvent.click(screen.getByRole('button', { name: 'Wade in · 30m' }))
    expect(wadeIn).toHaveBeenCalled()
  })

  it('shows what the tide left behind', () => {
    seed({
      lastSalvage: {
        id: 'sealed_crate',
        text: 'A crate wedged under the walkway.',
        item: 'stim_tea',
        item_name: 'Stim Tea',
      },
    })
    render(<TideLineView />)
    expect(screen.getByText(/crate wedged/)).toBeInTheDocument()
    expect(screen.getByText(/◈ Stim Tea/)).toBeInTheDocument()
  })
})
