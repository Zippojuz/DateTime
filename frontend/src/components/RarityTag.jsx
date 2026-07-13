// Small colored rarity chip, shared by inventory / shop / gift views.
export default function RarityTag({ rarity }) {
  if (!rarity) return null
  return <span className={`rarity rarity--${rarity}`}>{rarity}</span>
}
