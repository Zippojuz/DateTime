import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import RelationshipPanel from './RelationshipPanel'
import { useGameStore } from '../state/gameStore'

const CHARACTERS = [
  { id: 'oona', name: 'Oona', pronouns: 'she/her', met: true, affection: 12, stage: 'acquaintance', preferences: {} },
  { id: 'vex', name: 'Mama Vex', pronouns: 'she/her', met: false, affection: 0, stage: 'stranger', preferences: {} },
]

describe('RelationshipPanel', () => {
  beforeEach(() => useGameStore.setState({ characters: CHARACTERS }))

  it('shows only people you have met', () => {
    render(<RelationshipPanel />)
    expect(screen.getByText('Oona')).toBeInTheDocument()
    expect(screen.queryByText('Mama Vex')).not.toBeInTheDocument()
  })

  it('prompts you to go out when you have met no one', () => {
    useGameStore.setState({ characters: [{ ...CHARACTERS[1] }] })
    render(<RelationshipPanel />)
    expect(screen.getByText(/haven't met anyone yet/)).toBeInTheDocument()
    expect(screen.queryByText('Mama Vex')).not.toBeInTheDocument()
  })
})
