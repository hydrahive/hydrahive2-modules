/** Reine Logik des Reiters Entrümpeln (ohne React), einzeln testbar. */
import type { DebloatGroup, TvwDebloatRow, TvwDebloatView } from "./api"

export const GROUP_ORDER: DebloatGroup[] = ["tracking", "ads", "demo", "home", "help", "other"]

/** Empfohlene Pakete nach Gruppe (Reihenfolge wie GROUP_ORDER), danach der Rest als eigener Block. */
export function grouped(v: TvwDebloatView): { group: DebloatGroup; rows: TvwDebloatRow[] }[] {
  const rec = v.packages.filter((r) => r.recommended)
  return GROUP_ORDER.map((g) => ({ group: g, rows: rec.filter((r) => r.group === g) })).filter((x) => x.rows.length)
}

/** Nicht empfohlen, aber in einer passenden Liste genannt oder schon aus – „Weitere“. */
export function others(v: TvwDebloatView): TvwDebloatRow[] {
  return v.packages.filter((r) => !r.recommended)
}

/** Kennzeichen eines Pakets: aus, gesperrt, empfohlen-und-noch-an oder an. */
export type Mark = "off" | "locked" | "todo" | "on"
export function mark(r: TvwDebloatRow): Mark {
  if (r.locked) return "locked"
  if (r.state === "off") return "off"
  return r.recommended ? "todo" : "on"
}

/** Kurzer Name einer Liste: Ordner ohne „/debloat.txt“. */
export function listName(path: string): string {
  return path.replace(/\/debloat[^/]*\.txt$/, "")
}

/** Geräteordner der Listen, jeder nur einmal (ein Ordner kann zwei Listen haben), sortiert. */
export function listNames(paths: string[]): string {
  return [...new Set(paths.map(listName))].sort().join(", ")
}

/** Was ein Haken auslösen würde: abschalten (an, nicht gesperrt) oder wieder einschalten (aus, nicht gesperrt). */
export function canPick(r: TvwDebloatRow): boolean {
  return !r.locked
}

/** Auswahl aufteilen: was angeht ist „aus“, was ausgeht ist „an“. Gesperrte und Unbekannte fallen weg. */
export function split(v: TvwDebloatView, picked: Set<string>): { off: string[]; on: string[] } {
  const rows = v.packages.filter((r) => picked.has(r.package) && canPick(r))
  return { off: rows.filter((r) => r.state === "on").map((r) => r.package),
    on: rows.filter((r) => r.state === "off").map((r) => r.package) }
}

/** Vorschlag zum Anhaken: empfohlen, noch an, nicht gesperrt. */
export function suggested(v: TvwDebloatView): string[] {
  return v.packages.filter((r) => r.recommended && r.state === "on" && !r.locked).map((r) => r.package)
}

/** Schritt eines Auftrags als Text-Schlüssel und Werte („batch 2“ → Schub 2). */
export function stepText(step: string): { key: string; n?: number } {
  const m = step.match(/^batch (\d+)$/)
  if (m) return { key: "deb.step.batch", n: Number(m[1]) }
  return { key: `deb.step.${["container", "lists", "packages", "guard", "backup", "restore", "read"].includes(step)
    ? step : "other"}` }
}
