import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DialogueScreen from './DialogueScreen'
import { useGameStore } from '../state/gameStore'

const NODE = {
  node_id: 'n1',
  text: 'You again.',
  choices: [
    { index: 0, text: 'Hello.', locked: false, requires: null },
    { index: 1, text: '[Charm] Nice place.', locked: true, requires: { charm: 6 } },
  ],
}

beforeEach(() => {
  useGameStore.setState({
    busy: false,
    error: null,
    dialogue: { npcId: 'vael', npcName: 'Vael', tier: 'full', node: NODE, lastGained: 0 },
  })
})

describe('DialogueScreen', () => {
  it('renders the node text and choices', () => {
    render(<DialogueScreen />)
    expect(screen.getByText('You again.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Hello\./ })).toBeEnabled()
  })

  it('disables a locked choice and shows its requirement', () => {
    render(<DialogueScreen />)
    const locked = screen.getByRole('button', { name: /Nice place/ })
    expect(locked).toBeDisabled()
    expect(screen.getByText(/needs charm 6/)).toBeInTheDocument()
  })

  it('advances to the next node on an available choice', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            ended: false,
            gained: 2,
            affection: 2,
            node: { node_id: 'n2', text: 'Sit, then.', choices: [] },
          }),
      }),
    )

    render(<DialogueScreen />)
    fireEvent.click(screen.getByRole('button', { name: /Hello\./ }))

    await waitFor(() => expect(screen.getByText('Sit, then.')).toBeInTheDocument())
    expect(screen.getByText(/\+2/)).toBeInTheDocument()
  })
})
