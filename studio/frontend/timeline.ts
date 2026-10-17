/** Rechenhilfen der Zeitleiste (Etappe 0: Anzeige; ab Etappe 2 auch Bearbeiten). */

export interface Viewport {
  /** Sichtbarer Bereich in Sekunden. */
  start: number
  span: number
}

export function clampViewport(v: Viewport, total: number): Viewport {
  const span = Math.min(Math.max(v.span, 2), total)
  const start = Math.min(Math.max(v.start, 0), total - span)
  return { start, span }
}

/** Position (0..1) eines Zeitpunkts im Ausschnitt; außerhalb < 0 oder > 1. */
export function toFraction(t: number, v: Viewport): number {
  return (t - v.start) / v.span
}

/** Zoom um einen Ankerpunkt (0..1 im Ausschnitt): factor < 1 = hinein, > 1 = hinaus. */
export function zoom(v: Viewport, factor: number, anchor: number, total: number): Viewport {
  const at = v.start + anchor * v.span
  const span = v.span * factor
  return clampViewport({ start: at - anchor * span, span }, total)
}

/** Übersichtsleiste: Klick/Ziehen bei `fraction` (0..1 des ganzen Films) zentriert den Ausschnitt dort. */
export function centerAt(v: Viewport, fraction: number, total: number): Viewport {
  return clampViewport({ start: fraction * total - v.span / 2, span: v.span }, total)
}

/** Zeitcode hh:mm:ss:ff bei `fps` Bildern pro Sekunde. */
export function timecode(t: number, fps = 25): string {
  const total = Math.max(0, Math.round(t * fps))
  const f = total % fps
  const s = Math.floor(total / fps)
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}:${pad(f)}`
}

/** Sinnvoller Abstand der Zeitmarken für den Ausschnitt (≈ 8–12 Marken). */
export function tickStep(span: number): number {
  const steps = [0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300]
  return steps.find((s) => span / s <= 12) ?? 600
}
