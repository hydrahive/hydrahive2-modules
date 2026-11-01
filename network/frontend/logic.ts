/** Reine Hilfsfunktionen des Moduls Netzwerk – ohne React, gut zu testen. */

export const BASE = "/modules/network"
const ERR = new Set(["network_not_configured", "network_url_invalid", "network_host_not_local", "network_credential_invalid",
  "network_unreachable", "network_auth_failed", "network_cert_unconfirmed", "network_cert_changed",
  "network_fingerprint_mismatch", "network_bad_response", "network_import_invalid", "network_value_invalid"])

export type Path = "cable" | "mobile" | "none" | "unknown"
export interface Sample {
  ts: number; lan_loss: number | null; lan_rtt: number | null; fritz_loss: number | null; fritz_rtt: number | null
  inet_loss: number | null; inet_rtt_min: number | null; inet_rtt_avg: number | null; inet_rtt_max: number | null
  inet_jitter: number | null; fritz_link: string | null; fritz_conn: string | null; fritz_access: string | null; path: Path
}
export interface Outage { start: number; end: number; kind: "wan" | "blip" | "internet" | "cable"; source: "udm" | "probe" }
export interface Speedtest { source: string; ts: number; down_mbit: number | null; up_mbit: number | null; ping_ms: number | null; server: string | null }
export type Light = "ok" | "warn" | "bad" | "unknown"

export function errorKey(e: unknown): string {
  const code = typeof e === "object" && e !== null ? (e as { code?: unknown }).code : undefined
  if (code === "capability_denied") return "err.network_configure_only"
  return typeof code === "string" && ERR.has(code) ? `err.${code}` : "err.general"
}

/** Dauer in Sekunden als kurzer deutscher Text: 30660 → „8 Std. 31 Min.“ */
export function duration(sec: number, t: (k: string, o?: Record<string, unknown>) => string): string {
  const s = Math.max(0, Math.round(sec))
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60)
  if (d) return t("dur.dh", { d, h })
  if (h) return t("dur.hm", { h, m })
  if (m) return t("dur.m", { m })
  return t("dur.s", { s })
}

/** Ampel für einen Abschnitt aus Verlust (Prozent) und Antwortzeit (ms). */
export function light(loss: number | null | undefined, rtt: number | null | undefined, warnMs: number): Light {
  if (loss === null || loss === undefined) return "unknown"
  if (loss >= 100) return "bad"
  if (loss > 0 || (rtt !== null && rtt !== undefined && rtt > warnMs)) return "warn"
  return "ok"
}

/** Speedtest gegen Tarif in Prozent (gerundet); ohne Tarif oder Messwert → null. */
export function percentOfPlan(value: number | null, plan: number | null | undefined): number | null {
  if (value === null || !plan) return null
  return Math.round((value / plan) * 100)
}

/** Störungen eines Tages (YYYY-MM-DD → Sekunden) als Liste, neueste zuerst, nur Tage mit Störung. */
export function dayRows(perDay: Record<string, number>): { day: string; seconds: number }[] {
  return Object.entries(perDay).filter(([, s]) => s > 0).map(([day, seconds]) => ({ day, seconds }))
    .sort((a, b) => b.day.localeCompare(a.day))
}

/** Punkte fürs Diagramm: Minutenwerte, verlorene Minuten als eigene Reihe (Höhe = Verlust). */
export function chartPoints(samples: Sample[]): { ts: number; rtt: number | null; loss: number; path: Path }[] {
  return samples.map((s) => ({ ts: s.ts, rtt: s.inet_rtt_avg, loss: s.inet_loss ?? 0, path: s.path }))
}

/** Einfache Prüfung der Adresse vor dem Senden (genau prüft der Server). */
export function looksLikeUdmUrl(v: string): boolean {
  return /^https:\/\/[a-z0-9.-]+(:\d{1,5})?\/?$/i.test(v.trim())
}
