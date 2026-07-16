import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import LoginScreen from './LoginScreen'
import { useGameStore } from '../state/gameStore'

describe('LoginScreen', () => {
  beforeEach(() => useGameStore.setState({ busy: false, error: null }))

  it('logs in with the form', () => {
    const loginAccount = vi.fn()
    useGameStore.setState({ loginAccount })
    render(<LoginScreen />)
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'kai' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'hunter22' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enter the city' }))
    expect(loginAccount).toHaveBeenCalledWith('kai', 'hunter22')
  })

  it('registers through the other tab', () => {
    const registerAccount = vi.fn()
    useGameStore.setState({ registerAccount })
    render(<LoginScreen />)
    fireEvent.click(screen.getByRole('button', { name: 'New account' }))
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'wren' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'hunter22' } })
    fireEvent.click(screen.getByRole('button', { name: 'Register' }))
    expect(registerAccount).toHaveBeenCalledWith('wren', 'hunter22')
  })

  it('shows the server refusal', () => {
    useGameStore.setState({ error: 'Wrong name or password. The door stays shut.' })
    render(<LoginScreen />)
    expect(screen.getByText(/door stays shut/)).toBeInTheDocument()
  })
})
