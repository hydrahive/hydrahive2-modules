import type { Connection, ConnectionIn, ConnectionStatus } from "./types"

/** Reine Logik der Einstellungsseite (ohne React) – getestet in connectionLogic.test.ts. */

export const DEFAULTS: ConnectionIn = {
  pbx: "fritzbox",
  display_name: "HydraHive",
  registrar: "fritz.box",
  registrar_port: 5060,
  username: "",
  password: "",
  own_number: "",
  local_sip_port: 5070,
  rtp_port_min: 7078,
  rtp_port_max: 7109,
  register_interval: 300,
}

/** Formular aus gespeicherter Verbindung – das Kennwort kommt nie vom Server, Feld bleibt leer. */
export function formFrom(conn: Connection | null): ConnectionIn {
  if (!conn || !conn.configured) return { ...DEFAULTS }
  const { pbx, display_name, registrar, registrar_port, username, own_number, local_sip_port, rtp_port_min,
    rtp_port_max, register_interval } = conn
  return { pbx, display_name, registrar, registrar_port, username, own_number, local_sip_port, rtp_port_min,
    rtp_port_max, register_interval, password: "" }
}

export type Tone = "ok" | "busy" | "warn" | "error" | "idle"

export function toneOf(status: ConnectionStatus): Tone {
  if (status === "registered") return "ok"
  if (status === "connecting") return "busy"
  if (status === "unreachable" || status === "rejected") return "warn"
  if (status === "disconnected" || status === "not_configured") return "idle"
  return "error"
}

/** Kann gespeichert werden? Neu: Kennwort Pflicht. FRITZ!Box: Benutzer und Kennwort je ≥ 8. */
export function canSave(form: ConnectionIn, hasPassword: boolean): boolean {
  if (!form.registrar.trim() || !form.username.trim()) return false
  if (!hasPassword && !form.password) return false
  if (form.pbx === "fritzbox") {
    if (form.username.trim().length < 8) return false
    if (form.password && form.password.length < 8) return false
  }
  return true
}

/** Hat sich gegenüber dem Gespeicherten etwas geändert? (Kennwort eingetippt zählt mit – gespeichert ist es "".) */
export function isDirty(form: ConnectionIn, conn: Connection | null): boolean {
  const saved = formFrom(conn)
  return (Object.keys(saved) as (keyof ConnectionIn)[]).some((k) => form[k] !== saved[k])
}

/** Fehlercode der API → Schlüssel in conn.errors (Unbekanntes → unknown). */
export function errorKey(code: string | undefined): string {
  const known = ["invalid", "blocked", "password_required", "port_taken", "rate_limited", "capability_denied"]
  return code && known.includes(code) ? code : "unknown"
}
