/** Reiter „Ausgabe“ (4d, 7b): reine Hilfen, damit testbar. Größen wie auf dem Server (backend/render_preset.py). */
import type { RenderItem } from "./renderApi"
import type { TimelineClip } from "./timelineApi"

const RATIOS: Record<string, [number, number]> = { "16:9": [16, 9], "9:16": [9, 16], "1:1": [1, 1], "4:3": [4, 3], "21:9": [21, 9] }
/** wählbare Formate; „screenplay“ = Format des Drehbuchs */
export const ASPECTS = ["screenplay", "16:9", "9:16", "1:1"] as const
/** wählbare Qualitäten = kürzere Seite (Vorschau 480p, Standard 720p, Hoch 1080p) */
export const QUALITIES = ["preview", "standard", "high"] as const
const SHORT: Record<string, number> = { preview: 480, standard: 720, high: 1080 }

export type Aspect = (typeof ASPECTS)[number]
export type Quality = (typeof QUALITIES)[number]
export interface Preset { aspect: Aspect; quality: Quality }
export const DEFAULT_PRESET: Preset = { aspect: "screenplay", quality: "standard" }

type T = (k: string, o?: Record<string, unknown>) => string

const even = (x: number) => Math.round(x / 2) * 2

/** Ausgabegröße: kürzere Seite = Qualität, längere aus dem Format (gerade gerundet); „screenplay“ nimmt das Drehbuch. */
export function outputSize(aspect: string, quality: string, screenplay: string): [number, number] {
  const [rw, rh] = RATIOS[aspect === "screenplay" ? screenplay : aspect] ?? RATIOS["16:9"]
  const short = SHORT[quality] ?? SHORT.standard
  return rw >= rh ? [even((short * rw) / rh), short] : [short, even((short * rh) / rw)]
}

/** „9:16 · Standard 720p“ für einen fertigen Film; ohne Vorlage (ältere Filme) leer. */
export function presetLabel(t: T, r: { aspect?: string | null; quality?: string | null }): string {
  return r.aspect && r.quality ? t("deliver_film_preset", { aspect: r.aspect, quality: t(`deliver_quality.${r.quality}`) }) : ""
}

/** Name beim Herunterladen: film-<Zeit>-<Format>-<kürzere Seite>p.mp4; ältere Filme: Breite×Höhe. */
export function downloadName(r: RenderItem): string {
  const stamp = (r.created_at || "").slice(0, 16).replace(/[^0-9]/g, "")
  if (!stamp) return `film-${r.name}`
  const size = r.aspect && r.width && r.height ? `-${r.aspect.replace(":", "x")}-${Math.min(r.width, r.height)}p`
    : r.width && r.height ? `-${r.width}x${r.height}` : ""
  return `film-${stamp}${size}.mp4`
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
