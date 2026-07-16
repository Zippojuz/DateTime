import { useState } from 'react'
import { useGameStore } from '../state/gameStore'
import RarityTag from './RarityTag.jsx'

const SLOT_LABEL = {
  weapon: 'Weapon',
  head: 'Head',
  torso: 'Torso',
  arms: 'Arms',
  hands: 'Hands',
  legs: 'Legs',
  feet: 'Feet',
  ring1: 'Ring I',
  ring2: 'Ring II',
  accessory: 'Accessory',
  aug_neural: 'Neural',
  aug_ocular: 'Ocular',
  aug_dermal: 'Dermal',
  aug_skeletal: 'Skeletal',
}

// Paper doll: rough body shape via grid-template-areas (see styles.css).
const GEAR_SLOTS = [
  'head',
  'weapon',
  'torso',
  'accessory',
  'arms',
  'legs',
  'hands',
  'ring1',
  'feet',
  'ring2',
]
const AUG_SLOTS = ['aug_neural', 'aug_ocular', 'aug_dermal', 'aug_skeletal']

const BONUS_LABEL = {
  attack: 'ATK',
  defense: 'DEF',
  max_hp: 'HP',
  speed: 'SPD',
  dodge: 'DODGE',
  heat_cap: 'HEAT',
  heat_vent: 'VENT',
}

// Rings declare slot "ring" and fit either finger.
function slotsFor(item) {
  return item.slot === 'ring' ? ['ring1', 'ring2'] : [item.slot]
}

function bonusText(item) {
  const b = item.bonuses ?? {}
  const parts = Object.entries(BONUS_LABEL)
    .filter(([key]) => b[key])
    .map(([key, label]) => {
      const val = key === 'dodge' ? `${Math.round(b[key] * 100)}%` : b[key]
      return `${b[key] > 0 ? '+' : ''}${val} ${label}`
    })
  if (item.sockets) parts.push(`◇×${item.sockets}`)
  return parts.join(' · ')
}

// The loadout screen: your pack on one side, a paper-doll grid of slots on the
// other. Pick a piece of gear, then tap a glowing slot to wear it. Tap a worn
// slot to inspect it — sockets and removal live in the detail card.
export default function EquipmentPanel() {
  const equipment = useGameStore((s) => s.equipment)
  const items = useGameStore((s) => s.items)
  const inventory = useGameStore((s) => s.state?.player?.inventory ?? {})
  const equipItem = useGameStore((s) => s.equipItem)
  const unequipSlot = useGameStore((s) => s.unequipSlot)
  const socketGem = useGameStore((s) => s.socketGem)
  const unsocketGem = useGameStore((s) => s.unsocketGem)
  const busy = useGameStore((s) => s.busy)

  const [picked, setPicked] = useState(null) // item id lifted from the pack
  const [inspect, setInspect] = useState(null) // slot id under the loupe

  if (!equipment || !items) return null
  const { slots, stats, bonuses, augments } = equipment

  const pack = Object.entries(inventory).filter(
    ([id, qty]) => qty > 0 && ['equipment', 'augment'].includes(items[id]?.type),
  )
  const ownedGems = Object.entries(inventory).filter(
    ([id, qty]) => items[id]?.type === 'gem' && qty > 0,
  )

  const pickedItem = picked ? items[picked] : null
  const validSlots = new Set(pickedItem ? slotsFor(pickedItem) : [])
  const augsFull = augments && augments.installed >= augments.capacity
  // Swapping within an occupied aug slot is fine — only empty ones lock at cap.
  const isLocked = (slot) => AUG_SLOTS.includes(slot) && !slots[slot] && augsFull

  const pickItem = (id) => {
    setInspect(null)
    setPicked(picked === id ? null : id)
  }
  const clickCell = (slot) => {
    if (picked && validSlots.has(slot) && !isLocked(slot)) {
      equipItem(picked, slot)
      setPicked(null)
      setInspect(slot)
      return
    }
    setPicked(null)
    setInspect(inspect === slot ? null : slot)
  }

  const renderCell = (slot) => {
    const entry = slots[slot]
    const gear = entry ? items[entry.item] : null
    const locked = isLocked(slot)
    const cls = ['equip-cell']
    if (gear) cls.push('equip-cell--filled')
    if (validSlots.has(slot) && !locked) cls.push('equip-cell--valid')
    if (inspect === slot) cls.push('equip-cell--active')
    if (locked) cls.push('equip-cell--locked')
    return (
      <button
        key={slot}
        className={cls.join(' ')}
        style={GEAR_SLOTS.includes(slot) ? { gridArea: slot } : undefined}
        aria-label={`${SLOT_LABEL[slot]} slot`}
        disabled={busy}
        onClick={() => clickCell(slot)}
      >
        <span className="equip-cell-slot">{SLOT_LABEL[slot]}</span>
        <span className="equip-cell-item">{gear ? gear.name : locked ? '✕' : '—'}</span>
        {entry && entry.gems.length > 0 && (
          <span className="equip-cell-gems">
            {entry.gems.map((g) => (g ? '◈' : '◇')).join(' ')}
          </span>
        )}
      </button>
    )
  }

  const detailEntry = inspect ? slots[inspect] : null
  const detailGear = detailEntry ? items[detailEntry.item] : null

  return (
    <section className="equipment-panel">
      <h2>Loadout</h2>
      <p className="equip-stats">
        ATK {stats.attack} · DEF {stats.defense} · HP {stats.max_hp} · SPD {stats.speed} · CRIT{' '}
        {Math.round(stats.crit * 100)}% · DODGE {Math.round(stats.dodge * 100)}% · LACE{' '}
        {stats.protocol_power}
        {bonuses.weapon_element && (
          <span className={`element element--${bonuses.weapon_element}`}>
            {bonuses.weapon_element} strikes
          </span>
        )}
        {bonuses.auto_weakness && <span className="element">prisma strikes</span>}
      </p>
      {augments && (
        <p className="equip-augcap">
          Augments synced: {augments.installed}/{augments.capacity}
          <span className="equip-augcap-hint"> — hacking raises capacity (+1 per 5)</span>
        </p>
      )}
      <p className="equip-integrated" title="Standard issue. Doesn't use a slot.">
        ⬡ Cyberlink <span className="equip-augcap-hint">— integrated, standard issue</span>
      </p>

      <div className="loadout">
        <div className="loadout-pack">
          <h3>Pack</h3>
          {pack.length === 0 ? (
            <p className="equip-empty">Nothing equippable — try a shop or the substrate.</p>
          ) : (
            <ul className="pack-list">
              {pack.map(([id, qty]) => {
                const item = items[id]
                const sub = [
                  slotsFor(item)
                    .map((s) => SLOT_LABEL[s])
                    .join(' / '),
                  bonusText(item),
                ]
                  .filter(Boolean)
                  .join(' · ')
                return (
                  <li key={id}>
                    <button
                      className={`pack-item${picked === id ? ' pack-item--picked' : ''}`}
                      disabled={busy}
                      onClick={() => pickItem(id)}
                    >
                      <span className="pack-name">
                        {item.name}
                        {qty > 1 && ` ×${qty}`} <RarityTag rarity={item.rarity} />
                      </span>
                      <span className="pack-sub">{sub}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        <div className="loadout-doll">
          <h3>Body</h3>
          <div className="doll-grid">{GEAR_SLOTS.map(renderCell)}</div>
          <div className="aug-grid">{AUG_SLOTS.map(renderCell)}</div>

          {pickedItem && (
            <p className="equip-hint">
              Placing <strong>{pickedItem.name}</strong> — tap a glowing slot.
              {slotsFor(pickedItem)
                .filter((s) => slots[s])
                .map((s) => ` Swaps out ${items[slots[s].item]?.name} (${SLOT_LABEL[s]}).`)
                .join('')}
            </p>
          )}

          {!pickedItem && inspect && detailGear && (
            <div className="equip-detail">
              <span>
                {detailGear.name} <RarityTag rarity={detailGear.rarity} />
                <span className="equip-augcap-hint"> · {SLOT_LABEL[inspect]}</span>
              </span>
              <span className="pack-sub">{detailGear.description}</span>
              {bonusText(detailGear) && <span className="pack-sub">{bonusText(detailGear)}</span>}
              {detailEntry.gems.length > 0 && (
                <div className="equip-sockets">
                  {detailEntry.gems.map((gemId, i) =>
                    gemId ? (
                      <button
                        key={i}
                        className="gem gem--filled"
                        disabled={busy}
                        title={`${items[gemId]?.name}: ${items[gemId]?.description} (click to remove)`}
                        onClick={() => unsocketGem(inspect, i)}
                      >
                        ◈ {items[gemId]?.name}
                      </button>
                    ) : (
                      <select
                        key={i}
                        className="gem gem--empty"
                        disabled={busy || !ownedGems.length}
                        value=""
                        title="Socket a gem"
                        onChange={(e) => e.target.value && socketGem(inspect, e.target.value, i)}
                      >
                        <option value="">◇ empty socket</option>
                        {ownedGems.map(([id, qty]) => (
                          <option key={id} value={id}>
                            {items[id].name} ×{qty}
                          </option>
                        ))}
                      </select>
                    ),
                  )}
                </div>
              )}
              <button
                className="btn-action"
                disabled={busy}
                onClick={() => {
                  unequipSlot(inspect)
                  setInspect(null)
                }}
              >
                Remove
              </button>
            </div>
          )}

          {!pickedItem && inspect && !detailGear && (
            <p className="equip-hint">
              {isLocked(inspect)
                ? `Your lace is at capacity (${augments.installed}/${augments.capacity}) — train hacking to sync more.`
                : `Nothing on the ${SLOT_LABEL[inspect]} slot. Pick something from the pack that fits.`}
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
