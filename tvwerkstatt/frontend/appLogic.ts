/** Reine Logik der App-Geräte (ohne React), einzeln testbar. */
import type { TvwAppDevice } from "./api"

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
