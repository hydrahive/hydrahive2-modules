// Fremde Ideen anderer Instanzen (Gemeinsame Taskpflege, Spec federation-shared-tasks.md §Oberfläche):
// Umwandlung in Listenzeilen, Filter „Nur diese / Alle Instanzen“ (gemerkt), Zustand der Detailansicht.
import type { ForeignIdea, ForeignIdeaFull, IdeaListItem } from "./types"

export type InstanceScope = "all" | "local"

export const SCOPE_KEY = "hh.scratchpad.instances"
const PREFIX = "f:"

/** Listenzeile einer fremden Idee. Projekt = eigene Zuordnung, damit Projektfilter und Gruppen greifen. */
export interface ForeignListItem extends IdeaListItem {
  foreign: ForeignIdea
}

/** Kern-Zeitstempel sind sekundengenau, eigene mit Mikrosekunden: gleich lang machen, damit die
 *  Sortierung (Textvergleich in sortIdeas) bei gleicher Sekunde nicht kippt. */
function micro(stamp: string): string {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(stamp) ? `${stamp.slice(0, 19)}.000000Z` : stamp
}

export function toForeignItem(idea: ForeignIdea): ForeignListItem {
  return {
    id: `${PREFIX}${idea.origin_fp}:${idea.item_id}`, project_id: idea.local_project_id, title: idea.title,
    status: idea.status, origin: "user", task_id: null, board_id: null, created_at: micro(idea.created_at),
    updated_at: micro(idea.updated_at), body_preview: "", note_count: 0, foreign: idea,
  }
}

/** Antwort der Liste aufteilen: eigene unverändert, fremde als Listenzeilen. */
export function splitList(rows: ReadonlyArray<IdeaListItem | ForeignIdea>): IdeaListItem[] {
  return rows.map((row) => ((row as ForeignIdea).foreign === true ? toForeignItem(row as ForeignIdea) : row as IdeaListItem))
}

export function isForeignItem(item: IdeaListItem): item is ForeignListItem {
  return (item as ForeignListItem).foreign !== undefined
}

/** Geöffnete fremde Idee steht nicht mehr in der Liste (gelöscht oder nicht mehr sichtbar). */
export function foreignMissing(open: ForeignIdea | null, list: readonly IdeaListItem[]): boolean {
  if (open === null) return false
  return !list.some((row) => isForeignItem(row)
    && row.foreign.origin_fp === open.origin_fp && row.foreign.item_id === open.item_id)
}

/** Eigene Ideen nie mit einer fremden verwechseln: eigene IDs haben kein Präfix. */
export function isForeignId(id: string | null | undefined): boolean {
  return !!id && id.startsWith(PREFIX)
}

/** Gemerkte Auswahl. Standard „Alle Instanzen“ (Entscheidung 8), auch ohne localStorage. */
export function loadScope(storage: Pick<Storage, "getItem"> | null = safeStorage()): InstanceScope {
  try {
    return storage?.getItem(SCOPE_KEY) === "local" ? "local" : "all"
  } catch {
    return "all"
  }
}

export function saveScope(scope: InstanceScope, storage: Pick<Storage, "setItem"> | null = safeStorage()): void {
  try {
    storage?.setItem(SCOPE_KEY, scope)
  } catch {
    // privater Modus o. ä.: Auswahl gilt dann nur bis zum Neuladen
  }
}

function safeStorage(): Storage | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null
  } catch {
    return null
  }
}

export type DetailState = "live" | "snapshot" | "origin_offline" | "hub_unreachable"

/** Was die Detailansicht zeigt: Volltext live, Snapshot des Hubs, nur Metadaten. */
export function detailState(full: ForeignIdeaFull): DetailState {
  if (full.hub_unreachable) return "hub_unreachable"
  if (full.source === "live" && !full.origin_offline) return "live"
  if (full.source === "snapshot") return "snapshot"
  return "origin_offline"
}

/** Kern-Zeitstempel (sekundengenau oder mit Mikrosekunden) als lesbares Datum. */
export function foreignStamp(value: string | null | undefined, locale: string): string {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(locale.startsWith("de") ? "de" : "en", { dateStyle: "medium", timeStyle: "short" })
}
