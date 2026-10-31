/** Etappe „Programm“: Typen und reine Hilfen – ohne React, gut zu testen. */
import { BASE, errorKey } from "./logic"

export interface Program { mode: string; ref_id: string; notice: string; name: string; count: number; position: number; can_moderate: boolean }
export interface Playlist { id: string; name: string; count: number; order_mode: "ordered" | "shuffle"; at_end: "repeat" | "back" }
export interface PlaylistItem { pos: number; track_id: string; artist: string; title: string; duration_s: number | null; available: boolean }
export interface Rules {
  genres: string[]; artists: string[]; folders: string[]; decades: number[]
  exclude_genres: string[]; exclude_artists: string[]; exclude_folders: string[]
}
export interface Mix { id: string; name: string; rules: Partial<Rules>; allow_long: boolean }
export interface QueueItem { id: number; pos: number; track_id: string; artist: string; title: string; duration_s: number | null; added_by: string }
export interface Preview { count: number; examples: { track_id: string; artist: string; title: string; year: number | null; genre: string }[] }

export { BASE }
export const DECADES = [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020]
export const FEW = 20
const LIST_KEYS = ["genres", "artists", "folders", "exclude_genres", "exclude_artists", "exclude_folders"] as const

const ERR = new Set(["radiostream_playlist_not_found", "radiostream_mix_not_found", "radiostream_rule_invalid",
  "radiostream_name_invalid", "radiostream_too_many", "radiostream_playlist_invalid", "radiostream_queue_invalid",
  "radiostream_program_invalid", "radiostream_program_empty", "radiostream_track_not_found"])

export function programErrorKey(e: unknown): string {
  const code = typeof e === "object" && e !== null ? (e as { code?: unknown }).code : undefined
  if (code === "capability_denied") return "err.radiostream_moderate_only"
  return typeof code === "string" && ERR.has(code) ? `err.${code}` : errorKey(e)
}

export function programLine(p: Program): { key: string; opts?: Record<string, unknown> } {
  if (p.mode === "playlist") return { key: "program.line_playlist", opts: { name: p.name, pos: p.position, count: p.count } }
  if (p.mode === "mix") return { key: "program.line_mix", opts: { name: p.name, count: p.count } }
  return { key: "program.line_all" }
}

export function emptyRules(): Rules {
  return { genres: [], artists: [], folders: [], decades: [], exclude_genres: [], exclude_artists: [], exclude_folders: [] }
}

/** Mix-Regel aus dem Backend (nur gesetzte Felder) → vollständige Regel für den Editor. */
export function fullRules(r: Partial<Rules>): Rules {
  return { ...emptyRules(), ...r }
}

/** Nur gesetzte Felder schicken (Backend lehnt unbekannte ab, leere Listen sind überflüssig). */
export function compactRules(r: Rules): Partial<Rules> {
  const out: Partial<Rules> = {}
  for (const k of LIST_KEYS) if (r[k].length) out[k] = r[k]
  if (r.decades.length) out.decades = r.decades
  return out
}

export function rulesSummary(r: Rules): string[] {
  return [...r.genres, ...r.artists, ...r.folders, ...r.decades.map((d) => `${d}er`),
    ...[...r.exclude_genres, ...r.exclude_artists, ...r.exclude_folders].map((x) => `− ${x}`)]
}

/** Wert der Auswahl „Was soll laufen?“ ↔ Programm. */
export const programValue = (p: Pick<Program, "mode" | "ref_id">) => (p.mode === "all" ? "all" : `${p.mode}:${p.ref_id}`)
export function parseProgramValue(v: string): { mode: "all" | "playlist" | "mix"; ref_id: string } {
  const [mode, ref] = v.split(":")
  return mode === "playlist" || mode === "mix" ? { mode, ref_id: ref ?? "" } : { mode: "all", ref_id: "" }
}

/** Oberste Ordner aus Pfaden (für die Ordner-Auswahl im Mix). */
export function moveIndex(len: number, i: number, dir: -1 | 1): number | null {
  const j = i + dir
  return j < 0 || j >= len ? null : j
}

export const DRAG_TYPE = "application/x-radiostream-track"
