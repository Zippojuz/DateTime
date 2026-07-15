import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import GiftReactionCard from './GiftReactionCard'
import { useGameStore } from '../state/gameStore'

describe('GiftReactionCard', () => {
  it('renders nothing without a reaction', () => {
    useGameStore.setState({ lastReaction: null })
    const { container } = render(<GiftReactionCard />)
    expect(container).toBeEmptyDOMElement()
  })

  it('gives the item its own clause instead of doubling it onto the reaction verb', () => {
    // Regression: the old template appended "to the {item}" onto every
    // sentiment line ("accepts it politely to the Protein Cube"), which reads
    // broken for every sentiment, not just neutral.
    useGameStore.setState({
      lastReaction: { npcName: 'Carro', item: 'Protein Cube', sentiment: 'neutral', delta: 1 },
    })
    render(<GiftReactionCard />)
    expect(screen.getByText('You give Carro the Protein Cube. They accept it politely.')).toBeInTheDocument()
    expect(screen.queryByText(/politely to the/)).not.toBeInTheDocument()
  })

  it('shows the affection delta with a sign and dismisses on click', () => {
    const dismiss = () => useGameStore.setState({ lastReaction: null })
    useGameStore.setState({
      lastReaction: { npcName: 'Vael', item: 'First Edition', sentiment: 'love', delta: 7 },
      dismissReaction: dismiss,
    })
    render(<GiftReactionCard />)
    expect(screen.getByText('+7 ♥')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(useGameStore.getState().lastReaction).toBeNull()
  })
})
