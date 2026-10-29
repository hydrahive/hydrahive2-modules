/** Reine Hilfsfunktionen des Radiostreams (Etappe 1) – ohne React, gut zu testen. */

export const BASE = "/modules/radiostream"
const ERR = new Set(["radiostream_not_configured", "radiostream_url_invalid", "radiostream_credential_invalid",
  "radiostream_source_unreachable", "radiostream_auth_failed", "radiostream_share_not_found", "radiostream_scan_running",
  "radiostream_track_not_found", "radiostream_track_unavailable", "radiostream_admin_only", "radiostream_scan_interrupted"])

export interface Filter { q: string; genre: string; decade: string; format: string; missing: boolean }
export interface ScanState { running: boolean; done: number; todo: number; files_seen: number; eta_s: number | null }

export function errorKey(e: unknown): string {
  const code = typeof e === "object" && e !== null ? (e as { code?: unknown }).code : undefined
  return typeof code === "string" && ERR.has(code) ? `err.${code}` : "err.general"
}

export function tracksQuery(f: Filter, cursor: string): string {
  const p = new URLSearchParams({ limit: "200" })
  if (f.q.trim()) p.set("q", f.q.trim())
  if (f.genre) p.set("genre", f.genre)
  if (f.decade) {
    const d = Number(f.decade)
    p.set("year_from", String(d))
    p.set("year_to", String(d + 9))
  }
  if (f.format) p.set("format", f.format)
  if (f.missing) p.set("state", "missing")
  if (cursor) p.set("cursor", cursor)
  return `${BASE}/tracks?${p.toString()}`
}

export function isSmbUrl(url: string): boolean {
  const m = /^smb:\/\/([A-Za-z0-9._-]+)\/(.+)$/.exec(url.trim())
  if (!m) return false
  const parts = m[2].split("/").filter(Boolean)
  return parts.length > 0 && parts.every((p) => p !== "." && p !== "..")
}

export function fmtDuration(s: number | null | undefined): string {
  if (s == null) return "–"
  const t = Math.round(s)
  const h = Math.floor(t / 3600)
  const m = Math.floor((t % 3600) / 60)
  const sec = String(t % 60).padStart(2, "0")
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`
}

export function fmtTotal(s: number): { days: number; hours: number } {
  return { days: Math.floor(s / 86400), hours: Math.floor((s % 86400) / 3600) }
}

export function scanLabel(s: ScanState, lastError: string | null = null): { key: string; pct: number | null; eta_min: number | null } {
  if (!s.running && lastError === "radiostream_scan_interrupted") return { key: "scan.interrupted", pct: null, eta_min: null }
  if (!s.running) return { key: "scan.idle", pct: null, eta_min: null }
  if (!s.todo) return { key: "scan.listing", pct: null, eta_min: null }
  return { key: "scan.running", pct: Math.floor((s.done / s.todo) * 100), eta_min: s.eta_s == null ? null : Math.ceil(s.eta_s / 60) }
}

export function audioUrl(trackId: string, token: string): string {
  return `/api${BASE}/tracks/${trackId}/audio?token=${encodeURIComponent(token)}`
}

/** Safe-Eintrag, dessen Adresse zur Musikquelle passt (Schrägstrich am Ende egal). */
export function matchCredential(creds: { name: string; url_pattern: string }[], url: string): string | null {
  const norm = (u: string) => u.trim().replace(/\/+$/, "").toLowerCase()
  return creds.find((c) => norm(c.url_pattern) === norm(url))?.name ?? null
}
