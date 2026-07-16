import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PawnshopView from './PawnshopView'
import { useGameStore } from '../state/gameStore'

const ITEMS = {
  first_edition: { name: 'First Edition', rarity: 'rare', description: 'A real paper book.' },
  protein_cube: { name: 'Protein Cube', rarity: 'common', description: 'Chewy, grey.' },
}

function seed(over = {}) {
  useGameStore.setState({
    busy: false,
    items: ITEMS,
    state: { player: { location: 'forget_me_not', inventory: { first_edition: 1 } } },
    pawn: {
      venue: 'forget_me_not',
      minutes: 10,
      hold_days: 7,
      offers: { first_edition: 22 },
      shelf: [],
    },
    lastPawn: null,
    ...over,
  })
}

describe('PawnshopView', () => {
  beforeEach(() => seed())

  it('renders nothing away from the shop', () => {
    seed({ state: { player: { location: 'the_shallows', inventory: {} } } })
    const { container } = render(<PawnshopView />)
    expect(container).toBeEmptyDOMElement()
  })

  it('quotes what you carry and pawns on click', () => {
    const sellItem = vi.fn()
    useGameStore.setState({ sellItem })
    render(<PawnshopView />)
    expect(screen.getByText('First Edition ×1')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Pawn · 22cr' }))
    expect(sellItem).toHaveBeenCalledWith('first_edition')
  })

  it('keeps the shelf with days left and buys back', () => {
    const buybackItem = vi.fn()
    useGameStore.setState({ buybackItem })
    seed({
      pawn: {
        venue: 'forget_me_not',
        minutes: 10,
        hold_days: 7,
        offers: {},
        shelf: [{ item: 'protein_cube', name: 'Protein Cube', buyback: 2, days_left: 3, paid: 1, day: 1 }],
      },
      state: { player: { location: 'forget_me_not', inventory: {} } },
    })
    render(<PawnshopView />)
    expect(screen.getByText("3 days before it's sold on")).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Buy back · 2cr' }))
    expect(buybackItem).toHaveBeenCalledWith(0)
  })

  it('always mentions the back case', () => {
    render(<PawnshopView />)
    expect(screen.getByText(/MEMORIES — BY APPOINTMENT ONLY/)).toBeInTheDocument()
  })
})
