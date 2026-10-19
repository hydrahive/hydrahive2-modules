/** Farben mit Farbwähler (C4): reine Hilfen. Werte bleiben #rrggbb wie bisher (paletteFromText). */
export const MAX_COLORS = 12
const HEX = /^#[0-9a-f]{6}$/i

/** #abc → #aabbcc (das Farbfeld des Browsers kennt nur die lange Form); Unsinn → Grau. */
export function longHex(c: string): string {
  const m = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/i.exec(c)
  if (m) return `#${m[1]}${m[1]}${m[2]}${m[2]}${m[3]}${m[3]}`.toLowerCase()
  return HEX.test(c) ? c.toLowerCase() : "#888888"
}

export function colorSet(colors: string[], i: number, value: string): string[] {
  return HEX.test(value) ? colors.map((c, j) => (j === i ? value.toLowerCase() : c)) : colors
}

export function colorAdd(colors: string[]): string[] {
  return colors.length >= MAX_COLORS ? colors : [...colors, "#888888"]
}

export function colorRemove(colors: string[], i: number): string[] {
  return colors.filter((_, j) => j !== i)
}
