import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import PeoplePanel from './PeoplePanel'
import { useGameStore } from '../state/gameStore'

const avail = (district, tier = 'full') => ({
  available: tier !== 'unavailable' && tier !== 'missed',
  tier,
  district,
  location: district,
  activity: null,
  minutes_left: 90,
})

// oona is standing where you are; vex is across town; nyx is off-duty here.
const CHARACTERS = [
  { id: 'oona', name: 'Oona', here: true, reachable: true, talked_today: false, availability: avail('the_hold') },
  { id: 'vex', name: 'Mama Vex', here: false, reachable: false, talked_today: false, availability: avail('neon_bazaar') },
]

describe('PeoplePanel', () => {
  beforeEach(() => useGameStore.setState({ characters: CHARACTERS, districts: {}, venues: {}, busy: false }))

  it('shows only people in this area', () => {
    render(<PeoplePanel />)
    expect(screen.getByText('Oona')).toBeInTheDocument()
    expect(screen.queryByText('Mama Vex')).not.toBeInTheDocument()
  })

  it('says no one is around when the area is empty', () => {
    useGameStore.setState({ characters: [{ ...CHARACTERS[1] }] })
    render(<PeoplePanel />)
    expect(screen.getByText(/No one's around here/)).toBeInTheDocument()
  })
})
