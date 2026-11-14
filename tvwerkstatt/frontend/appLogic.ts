/** Reine Logik der App-Geräte (ohne React), einzeln testbar. */
import type { TvwAppDevice, TvwJob } from "./api"

/** Online, wenn das letzte Lebenszeichen höchstens 90 s her ist (die App meldet sich alle ~25 s). */
export function online(d: TvwAppDevice, now: Date): boolean {
  if (d.status !== "active" || !d.last_seen) return false
  const t = Date.parse(d.last_seen)
  return Number.isFinite(t) && now.getTime() - t <= 90_000
}

/** Zeile „Tablet · Galaxy Tab A · Android 9 · App 1.0“. */
export function appLine(d: TvwAppDevice): string {
  return [d.kind === "tv" ? "TV" : d.kind === "tablet" ? "Tablet" : "", d.model, d.android ? `Android ${d.android}` : "",
    d.app_version ? `App ${d.app_version}` : ""].filter(Boolean).join(" · ")
}

/** Knöpfe aus Komma-Text: höchstens 3, je höchstens 20 Zeichen, leere weg. */
export function buttonsOf(text: string): string[] {
  return text.split(",").map((s) => s.trim().slice(0, 20)).filter(Boolean).slice(0, 3)
}

/** Restzeit des Codes in Minuten (abgerundet, nie negativ). */
export function minutesLeft(expires: string, now: Date): number {
  const t = Date.parse(expires)
  return Number.isFinite(t) ? Math.max(0, Math.floor((t - now.getTime()) / 60_000)) : 0
}

/** Schritte des Auftrags „App bauen“ (backend/app_build.py). */
export const APP_BUILD_STEPS = ["container", "fetch", "verify", "unpack", "build", "collect"] as const

/** „Schritt n von m“; unbekannter Schritt → 0. */
export function appBuildStep(step: string): { n: number; total: number } {
  const i = (APP_BUILD_STEPS as readonly string[]).indexOf(step)
  return { n: i < 0 ? 0 : i + 1, total: APP_BUILD_STEPS.length }
}

/** Zustand des Bau-Bereichs: läuft, gescheitert (mit Fehler), fertig (App da), noch nie gebaut. */
export function appBuildView(job: TvwJob | null | undefined, hasApk: boolean): "running" | "failed" | "done" | "none" {
  if (job?.state === "running") return "running"
  if (job?.state === "failed") return "failed"
  return hasApk ? "done" : "none"
}
