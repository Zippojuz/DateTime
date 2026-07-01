import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CreationScreen from './CreationScreen'
import { useGameStore } from '../state/gameStore'

beforeEach(() => {
  useGameStore.setState({ busy: false, error: null, screen: 'creation' })
})

describe('CreationScreen', () => {
  it('keeps the arrive button disabled until a name is entered', () => {
    render(<CreationScreen />)
    const submit = screen.getByRole('button', { name: /Arrive in Nexus City/ })
    expect(submit).toBeDisabled()

    fireEvent.change(screen.getByPlaceholderText(/call you/), {
      target: { value: 'Kai' },
    })
    expect(submit).toBeEnabled()
  })

  it('submits the identity and enters play on success', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            player: { identity: { name: 'Kai' } },
            clock: { time: '08:00' },
          }),
      }),
    )

    render(<CreationScreen />)
    fireEvent.change(screen.getByPlaceholderText(/call you/), {
      target: { value: 'Kai' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Arrive in Nexus City/ }))

    await waitFor(() => expect(useGameStore.getState().screen).toBe('play'))
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/game/new',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('species is fixed to Human', () => {
    render(<CreationScreen />)
    const species = screen.getByDisplayValue('Human')
    expect(species).toBeDisabled()
  })
})
