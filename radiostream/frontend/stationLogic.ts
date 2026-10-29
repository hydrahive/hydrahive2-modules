/** Reiter „Sender“ (Etappe 2): Typen und reine Hilfen – ohne React, gut zu testen. */
import { errorKey } from "./logic"

export interface StationSettings {
  name: string; subtitle: string; artist_gap_min: number; title_gap_days: number; listen_port: number
  reach: "all" | "home" | "off"; max_listeners: number
}
export interface Played { track_id: string; played_at: string; artist: string; title: string }
export interface Station {
  installed: boolean; running: boolean; listeners: number; can_control: boolean
  now: { artist: string; title: string }; recent: Played[]; settings: StationSettings
}

const STATION_ERR = new Set(["radiostream_service_missing", "radiostream_service_failed", "radiostream_not_running",
  "radiostream_port_in_use", "radiostream_nginx_failed", "radiostream_port_invalid", "radiostream_station_invalid"])

export function stationErrorKey(e: unknown): string {
  const code = typeof e === "object" && e !== null ? (e as { code?: unknown }).code : undefined
  if (code === "capability_denied") return "err.radiostream_admin_only"
  return typeof code === "string" && STATION_ERR.has(code) ? `err.${code}` : errorKey(e)
}

/** Adresse der Hörer-Seite: gleicher Rechner wie die Oberfläche, anderer Port, immer http. */
export function listenerUrl(host: string, port: number): string {
  let h = host.trim()
  if (h.startsWith("[")) h = h.slice(0, h.indexOf("]") + 1)
  else if (h.split(":").length === 2) h = h.split(":")[0]
  else if (h.includes(":")) h = `[${h}]`
  return `http://${h}:${port}/`
}
