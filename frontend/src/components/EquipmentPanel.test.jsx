import { render, screen, fireEvent } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import EquipmentPanel from './EquipmentPanel'
import { useGameStore } from '../state/gameStore'

const ITEMS = {
  scrap_blade: {
    name: 'Scrap Blade',
    type: 'equipment',
    slot: 'weapon',
    rarity: 'common',
    bonuses: { attack: 3 },
    sockets: 1,
    description: 'Sharp enough.',
  },
  signal_ring: {
    name: 'Signal Ring',
    type: 'equipment',
    slot: 'ring',
    rarity: 'uncommon',
    bonuses: { speed: 1 },
    description: 'Hums faintly.',
  },
  star_ration: { name: 'Star Ration', type: 'food', description: 'Chalky.' },
}

function seed({ slots = {}, inventory = {} } = {}) {
  useGameStore.setState({
    items: ITEMS,
    busy: false,
    state: { player: { inventory } },
    equipment: {
      slots,
      slot_order: [],
      stats: {
        attack: 1,
        defense: 0,
        max_hp: 20,
        speed: 2,
        crit: 0.05,
        dodge: 0,
        protocol_power: 0,
      },
      bonuses: {},
      augments: { installed: 0, capacity: 1 },
    },
  })
}

describe('EquipmentPanel', () => {
  beforeEach(() => seed())

  it('lists only equippable items in the pack', () => {
    seed({ inventory: { scrap_blade: 1, signal_ring: 1, star_ration: 2 } })
    render(<EquipmentPanel />)
    expect(screen.getByText('Scrap Blade')).toBeInTheDocument()
    expect(screen.getByText('Signal Ring')).toBeInTheDocument()
    expect(screen.queryByText(/Star Ration/)).not.toBeInTheDocument()
  })

  it('equips into the slot you tap after picking from the pack', () => {
    const equipItem = vi.fn()
    seed({ inventory: { scrap_blade: 1 } })
    useGameStore.setState({ equipItem })
    render(<EquipmentPanel />)
    fireEvent.click(screen.getByRole('button', { name: /Scrap Blade/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Weapon slot' }))
    expect(equipItem).toHaveBeenCalledWith('scrap_blade', 'weapon')
  })

  it('lights up both fingers for a ring', () => {
    seed({ inventory: { signal_ring: 1 } })
    render(<EquipmentPanel />)
    fireEvent.click(screen.getByRole('button', { name: /Signal Ring/ }))
    expect(screen.getByRole('button', { name: 'Ring I slot' })).toHaveClass('equip-cell--valid')
    expect(screen.getByRole('button', { name: 'Ring II slot' })).toHaveClass('equip-cell--valid')
    expect(screen.getByRole('button', { name: 'Weapon slot' })).not.toHaveClass(
      'equip-cell--valid',
    )
  })

  it('inspecting a worn slot offers removal', () => {
    const unequipSlot = vi.fn()
    seed({ slots: { weapon: { item: 'scrap_blade', gems: [null] } } })
    useGameStore.setState({ unequipSlot })
    render(<EquipmentPanel />)
    fireEvent.click(screen.getByRole('button', { name: 'Weapon slot' }))
    expect(screen.getByText('Sharp enough.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(unequipSlot).toHaveBeenCalledWith('weapon')
  })
})
