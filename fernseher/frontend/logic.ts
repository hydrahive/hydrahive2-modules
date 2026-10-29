/** Reine Hilfsfunktionen des Fernseher-Moduls – ohne React, gut zu testen. */

export const BASE = "/modules/fernseher"

export const ERROR_CODES = new Set([
  "tv_not_configured", "tv_unreachable", "tv_auth_failed", "tv_needs_restart", "tv_address_not_local",
  "tv_psk_missing", "tv_settings_invalid", "tv_channel_unknown", "tv_channel_ambiguous", "tv_app_unknown",
  "tv_volume_limit", "tv_volume_invalid", "tv_upstream_error", "tv_switch_failed",
])

export function errorKey(e: unknown): string {
  const code = typeof e === "object" && e !== null ? (e as { code?: unknown }).code : undefined
  return typeof code === "string" && ERROR_CODES.has(code) ? `err.${code}` : "err.general"
}

const LOCAL_SUFFIXES = [".local", ".lan", ".home", ".fritz.box", ".intra", ".internal", ".home.arpa"]
const LABEL = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/

function privateIPv4(addr: string): boolean | null {
  const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(addr)
  if (!m) return null
  const [a, b, c, d] = m.slice(1).map(Number)
  if ([a, b, c, d].some((n) => n > 255)) return false
  return a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168)
}

/** Nur ein Hinweis in der Oberfläche – entschieden wird im Backend (validators.normalize_address). */
export function isLocalAddress(raw: string): boolean {
  const addr = raw.trim().toLowerCase()
  if (!addr || addr === "localhost") return false
  const ip = privateIPv4(addr)
  if (ip !== null) return ip
  const labels = addr.split(".")
  if (!labels.every((l) => LABEL.test(l))) return false
  return labels.length === 1 || LOCAL_SUFFIXES.some((s) => addr.endsWith(s))
}

export function stepVolume(delta: number): string {
  return delta < 0 ? String(delta) : `+${delta}`
}

/** Ohne Suche zeigt die Fernbedienung nur die ersten Sender – der Fernseher kennt oft 300. */
export const CHANNELS_SHOWN = 20

const squash = (t: string) => t.toLowerCase().replace(/[^a-z0-9äöüß]/g, "")

export function filterChannels<T extends { number: number; name: string }>(all: T[], query: string): T[] {
  const q = squash(query)
  if (!q) return all.slice(0, CHANNELS_SHOWN)
  const hits = /^\d+$/.test(q)
    ? all.filter((c) => String(c.number) === q)
    : all.filter((c) => squash(c.name).includes(q))
  return hits.slice(0, CHANNELS_SHOWN)
}
