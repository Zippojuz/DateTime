import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TitleScreen from './TitleScreen'

beforeEach(() => {
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', game: 'nexus-city' }),
    }),
  )
})

describe('TitleScreen', () => {
  it('renders the logo and tagline', async () => {
    render(<TitleScreen />)
    expect(screen.getByText('NEXUS CITY')).toBeInTheDocument()
    expect(screen.getByText(/never sleeps/)).toBeInTheDocument()
    // Let the health check settle so the async state update stays inside act().
    await waitFor(() =>
      expect(screen.getByText(/Connected to Nexus core/)).toBeInTheDocument(),
    )
  })

  it('confirms the backend connection after the health check', async () => {
    render(<TitleScreen />)
    await waitFor(() =>
      expect(screen.getByText(/Connected to Nexus core/)).toBeInTheDocument(),
    )
  })
})
