// Fremde Tasks anderer Instanzen (Gemeinsame Taskpflege, Spec federation-shared-tasks.md §Oberfläche):
// Filter „Nur diese / Alle Instanzen“ (gemerkt je Modul) und Zustand der Detailansicht.
import { isForeign, type AnyTask, type ForeignTaskFull } from "./types"

export type InstanceScope = "all" | "local"

export const SCOPE_KEY = "hh.tasks.instances"

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

/** Was die Detailansicht anzeigt: Volltext live, Snapshot des Hubs, nur Metadaten. */
export function detailState(full: ForeignTaskFull): DetailState {
  if (full.hub_unreachable) return "hub_unreachable"
  if (full.source === "live" && !full.origin_offline) return "live"
  if (full.source === "snapshot") return "snapshot"
  return "origin_offline"
}

export function formatStamp(stamp: string | null | undefined, lang: string): string {
  if (!stamp) return "–"
  const date = new Date(stamp)
  if (Number.isNaN(date.getTime())) return stamp
  return date.toLocaleString(lang === "en" ? "en-GB" : "de-DE", { dateStyle: "short", timeStyle: "short" })
}

const PRIORITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 }

/** Eigene und fremde zusammen, sortiert wie die eigene Liste (Priorität, angelegt, ID). */
export function mergeSorted(own: AnyTask[], foreign: AnyTask[]): AnyTask[] {
  const key = (t: AnyTask) => isForeign(t) ? t.item_id : t.id
  return [...own, ...foreign].sort((a, b) =>
    (PRIORITY_ORDER[a.priority] ?? 2) - (PRIORITY_ORDER[b.priority] ?? 2)
    || a.created_at.localeCompare(b.created_at)
    || key(a).localeCompare(key(b)))
}
