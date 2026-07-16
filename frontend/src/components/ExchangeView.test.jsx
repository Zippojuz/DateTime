import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import ExchangeView from './ExchangeView'
import { useGameStore } from '../state/gameStore'

const CORPS = {
  corps: {
    oceania: {
      id: 'oceania',
      name: 'Oceania Consolidated',
      slogan: 'SAFETY IS FREEDOM',
      sector: 'Surveillance',
      blurb: 'Watching, kindly.',
      voice: 'Warm.',
      denial: 'No parent company. Never had one.',
    },
    eastasia: {
      id: 'eastasia',
      name: 'Eastasia Transcendence',
      slogan: 'THE SELF IS A DOOR',
      sector: 'Ego-loss',
      blurb: 'The exit from yourself.',
      voice: 'Serene.',
      denial: 'The question is an illusion.',
    },
  },
  war: {
    allies: ['oceania', 'eurasia'],
    enemy: 'eastasia',
    line: 'Oceania and Eurasia have always stood together against Eastasia. Always.',
    bulletin: 'Records indicating otherwise have been corrected.',
  },
}

function seed(over = {}) {
  useGameStore.setState({
    state: { player: { location: 'triumvirate_exchange' } },
    corps: CORPS,
    ...over,
  })
}

describe('ExchangeView', () => {
  beforeEach(() => seed())

  it('renders nothing outside the atrium', () => {
    seed({ state: { player: { location: 'citadel_ring' } } })
    const { container } = render(<ExchangeView />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows three voices and this week of the eternal war', () => {
    render(<ExchangeView />)
    expect(screen.getByText(/have always stood together/)).toBeInTheDocument()
    expect(screen.getByText(/have been corrected/)).toBeInTheDocument()
    expect(screen.getByText('SAFETY IS FREEDOM')).toBeInTheDocument()
    expect(screen.getByText('THE SELF IS A DOOR')).toBeInTheDocument()
    expect(screen.getByText('THIS WEEK: THE ENEMY')).toBeInTheDocument()
    expect(screen.getByText('THIS WEEK: ALLIED')).toBeInTheDocument()
    expect(screen.getByText(/question is an illusion/)).toBeInTheDocument()
  })
})
