/** Reiter „Ausgabe“ (4d): reine Hilfen, damit testbar. Größen wie auf dem Server (backend/render_args.py SIZES). */
import type { TimelineClip } from "./timelineApi"

const SIZES: Record<string, [number, number]> = {
  "16:9": [1280, 720], "9:16": [720, 1280], "1:1": [1080, 1080], "4:3": [960, 720], "21:9": [1680, 720],
}

export function filmSize(aspect: string): [number, number] {
  return SIZES[aspect] ?? SIZES["16:9"]
}

/** Länge bis zum Ende des letzten Clips (Lücken zählen mit), Zahl der Clips und Platzhalter. */
export function deliverSummary(clips: TimelineClip[]) {
  const seconds = clips.reduce((m, c) => Math.max(m, c.start + (c.out - c.in)), 0)
  return {
    seconds: Math.round(seconds * 1000) / 1000,
    clips: clips.length,
    placeholders: clips.filter((c) => c.kind === "placeholder").length,
    missing: clips.filter((c) => c.missing).length,
  }
}

/** 75.4 → „1:15“ (abgerundet wie in Abspielern: 12,5 s → „0:12“) */
export function minutes(seconds: number): string {
  const s = Math.floor(seconds + 1e-6)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`
}
