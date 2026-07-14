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
  aug_neural: 'Aug · Neural',
  aug_ocular: 'Aug · Ocular',
  aug_dermal: 'Aug · Dermal',
  aug_skeletal: 'Aug · Skeletal',
}

// Gear loadout: ten JRPG slots, each with gem sockets (materia-style — an
// element gem behaves differently in a weapon vs armor).
export default function EquipmentPanel() {
  const equipment = useGameStore((s) => s.equipment)
  const items = useGameStore((s) => s.items)
  const inventory = useGameStore((s) => s.state?.player?.inventory ?? {})
  const unequipSlot = useGameStore((s) => s.unequipSlot)
  const socketGem = useGameStore((s) => s.socketGem)
  const unsocketGem = useGameStore((s) => s.unsocketGem)
  const busy = useGameStore((s) => s.busy)

  if (!equipment || !items) return null
  const { slots, slot_order: order, stats, bonuses } = equipment

  const ownedGems = Object.entries(inventory).filter(
    ([id, qty]) => items[id]?.type === 'gem' && qty > 0,
  )

  return (
    <section className="equipment-panel">
      <h2>Equipment</h2>
      <p className="equip-stats">
        ATK {stats.attack} · DEF {stats.defense} · HP {stats.max_hp} · SPD {stats.speed} · CRIT{' '}
        {Math.round(stats.crit * 100)}% · DODGE {Math.round(stats.dodge * 100)}%
        {bonuses.weapon_element && (
          <span className={`element element--${bonuses.weapon_element}`}>
            {bonuses.weapon_element} strikes
          </span>
        )}
        {bonuses.auto_weakness && <span className="element">prisma strikes</span>}
      </p>
      <ul className="equip-list">
        {order.map((slot) => {
          const entry = slots[slot]
          const gear = entry ? items[entry.item] : null
          return (
            <li key={slot} className="equip-slot">
              <span className="equip-slot-name">{SLOT_LABEL[slot] ?? slot}</span>
              {gear ? (
                <div className="equip-gear">
                  <span>
                    {gear.name} <RarityTag rarity={gear.rarity} />
                  </span>
                  <div className="equip-sockets">
                    {entry.gems.map((gemId, i) =>
                      gemId ? (
                        <button
                          key={i}
                          className="gem gem--filled"
                          disabled={busy}
                          title={`${items[gemId]?.name}: ${items[gemId]?.description} (click to remove)`}
                          onClick={() => unsocketGem(slot, i)}
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
                          onChange={(e) => e.target.value && socketGem(slot, e.target.value, i)}
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
                  <button
                    className="btn-action"
                    disabled={busy}
                    onClick={() => unequipSlot(slot)}
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <span className="equip-empty">—</span>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
