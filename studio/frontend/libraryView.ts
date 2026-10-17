/** Reine Logik der Bibliothek: filtern, suchen, gruppieren, Projektwahl merken. Testbar ohne React. */
import type { LibraryItem, MediaKind, StudioProject } from "./api"

export type Filter = MediaKind | "all"
export const FILTERS: Filter[] = ["all", "video", "image", "music", "element"]

/** Ordner in der Bibliothek, in dieser Reihenfolge. */
export type Group = "ai" | "upload" | "atelier" | "videoeditor" | "tonstudio"

export function groupOf(i: LibraryItem): Group {
  return i.origin === "upload" ? "upload" : "ai"
}

export function visible(items: LibraryItem[], filter: Filter, query: string): LibraryItem[] {
  const q = query.trim().toLowerCase()
  return items.filter((i) => (filter === "all" || i.kind === filter || (filter === "music" && i.kind === "audio"))
    && (!q || i.name.toLowerCase().includes(q) || (i.prompt ?? "").toLowerCase().includes(q)))
}

export function grouped(items: LibraryItem[]): { group: Group; items: LibraryItem[] }[] {
  const order: Group[] = ["ai", "upload"]
  return order.map((group) => ({ group, items: items.filter((i) => groupOf(i) === group) })).filter((g) => g.items.length)
}

export const PROJECT_KEY = "hh.studio.project.v1"

/** Zuletzt gewähltes Projekt, falls es noch zugänglich ist – sonst das erste. */
export function pickProject(projects: StudioProject[], remembered: string | null): string {
  if (remembered && projects.some((p) => p.id === remembered)) return remembered
  return projects[0]?.id ?? ""
}

export function formatSize(bytes: number): string {
  const units = ["B", "KB", "MB", "GB"]
  let v = bytes
  let i = 0
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
  return i === 0 ? `${v} B` : `${v.toFixed(1)} ${units[i]}`
}

/** Was die Vorschau damit macht. */
export function previewMode(i: LibraryItem | null): "video" | "image" | "audio" | "element" | "none" {
  if (!i) return "none"
  if (i.kind === "video") return "video"
  if (i.kind === "image") return "image"
  if (i.kind === "element") return "element"
  return "audio"
}
