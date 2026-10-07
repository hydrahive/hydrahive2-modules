// Ghostwriter G4b – Vorschläge für Szenen-Infos (Titel, Zusammenfassung, Perspektive) ohne React:
// Server-Antwort → Markierung je Szene, Vergleich alt/neu, welche Felder übernommen werden.
import type { Scene } from "./model"

export type InfoField = "title" | "summary" | "pov"
export const INFO_FIELDS: InfoField[] = ["title", "summary", "pov"]

export interface InfoProposal {
  scene_id: string; fields: Partial<Record<InfoField, string>>; base_version: number
  source: "run" | "agent"; session_id: string; note: string; at: string
}

export function infoMarks(list: InfoProposal[] | undefined): Record<string, InfoProposal> {
  return Object.fromEntries((list ?? []).map((p) => [p.scene_id, p]))
}

export interface InfoRow { field: InfoField; old: string; proposed: string; same: boolean }

/** Zeilen für den Vergleich: nur Felder, die der Vorschlag enthält, in fester Reihenfolge. ``same`` = der Autor
 *  hat das Feld inzwischen selbst so gesetzt (Übernehmen ändert dann nichts). */
export function infoRows(p: InfoProposal, scene: Pick<Scene, InfoField>): InfoRow[] {
  return INFO_FIELDS.filter((f) => typeof p.fields[f] === "string")
    .map((f) => ({ field: f, old: scene[f], proposed: p.fields[f] as string, same: scene[f].trim() === (p.fields[f] as string).trim() }))
}

/** Auswahl für „Übernehmen“: angehakte Felder, die sich noch unterscheiden. Leer → nichts zu tun. */
export function chosenFields(rows: InfoRow[], checked: Partial<Record<InfoField, boolean>>): InfoField[] {
  return rows.filter((r) => !r.same && checked[r.field] !== false).map((r) => r.field)
}
