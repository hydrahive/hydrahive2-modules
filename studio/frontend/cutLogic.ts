/** Rechenhilfen für Schnitt und Wiedergabe (Etappe 4a). Rein, ohne DOM – damit testbar. */
import { clampViewport, type Viewport } from "./timeline"
import type { TimelineClip } from "./timelineApi"

export const clipLength = (c: TimelineClip): number => c.out - c.in

/** Filmlänge = Ende des spätesten Clips (Lücken zählen mit). */
export function filmLength(clips: TimelineClip[]): number {
  return clips.reduce((m, c) => Math.max(m, c.start + clipLength(c)), 0)
}

/** Clip, der bei t sichtbar ist (Start inklusive, Ende exklusiv); in Lücken null. */
export function activeAt(clips: TimelineClip[], t: number): TimelineClip | null {
  return clips.find((c) => t >= c.start && t < c.start + clipLength(c)) ?? null
}

/** Stelle im Medium für die Filmzeit t. */
export function sourceTime(c: TimelineClip, t: number): number {
  return c.in + (t - c.start)
}

/** Nächster Videoclip nach t – wird im zweiten Player vorgeladen, damit der Wechsel nicht ruckelt. */
export function nextMediaClip(clips: TimelineClip[], t: number): TimelineClip | null {
  return [...clips].sort((a, b) => a.start - b.start).find((c) => c.kind === "video" && c.start > t) ?? null
}

/** Sichtbarer Ausschnitt der Zeitleiste: an die Filmlänge angepasst; läuft der Abspielkopf hinaus, folgt er ihm. */
export function followView(v: Viewport, time: number, total: number): Viewport {
  const len = Math.max(total, 1)
  const fit = clampViewport(v, len)
  const outside = time < fit.start || time > fit.start + fit.span
  return outside ? clampViewport({ start: time - fit.span * 0.2, span: fit.span }, len) : fit
}
