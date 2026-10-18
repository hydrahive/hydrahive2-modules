/** Wellenform im Tonclip (5a): Ausschnitt verdichten. Rein, damit testbar. */
export const BARS = 120

/** Spitzenwerte des Ausschnitts, auf höchstens `bars` Balken verdichtet (jeweils der höchste Wert). */
export function slicePeaks(peaks: number[] | undefined, perSecond: number, from: number, to: number, bars = BARS): number[] {
  if (!peaks?.length || to <= from) return []
  const a = Math.max(0, Math.floor(from * perSecond))
  const b = Math.min(peaks.length, Math.ceil(to * perSecond))
  const part = peaks.slice(a, b)
  if (part.length <= bars) return part
  const step = part.length / bars
  return Array.from({ length: bars }, (_, i) => Math.max(...part.slice(Math.floor(i * step), Math.floor((i + 1) * step))))
}
