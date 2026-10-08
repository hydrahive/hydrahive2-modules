// A3 – Papierkorb (Spec nichts-geht-verloren.md §3): Aufrufe + reine Hilfen.
import { call, type ServerBook, type ServerScene, type ServerStructure } from "./api"

export interface TrashScene {
  id: string; scene_id: string; title: string; summary: string; words: number; deleted_at: string
  chapter_id: string; chapter_title: string; after: string; chapter_exists: boolean
}

export interface TrashBook {
  id: string; kind: "deleted" | "moved"; book_id: string; title: string; scenes: number; words: number
  deleted_at: string; restorable: boolean
}

export interface RestoredScene { placed: "original" | "end"; chapter_id: string; scene: ServerScene; structure: ServerStructure }

/** Wohin die Szene zurückkehrt – für den Hinweis vor dem Klick. */
export function whereBack(s: TrashScene): "original" | "end" {
  return s.chapter_exists ? "original" : "end"
}

/** Umzugs-Sicherungen nach unten, sonst neueste zuerst (Server liefert schon so; hier stabil für die Anzeige). */
export function sortBooks(rows: TrashBook[]): TrashBook[] {
  return [...rows].sort((a, b) => Number(a.kind === "moved") - Number(b.kind === "moved") || b.deleted_at.localeCompare(a.deleted_at))
}

const proj = (pid: string) => `/projects/${encodeURIComponent(pid)}`

export const trashApi = {
  scenes: (pid: string, bid: string) => call<TrashScene[]>("GET", `${proj(pid)}/books/${encodeURIComponent(bid)}/trash/scenes`),
  restoreScene: (pid: string, bid: string, id: string) =>
    call<RestoredScene>("POST", `${proj(pid)}/books/${encodeURIComponent(bid)}/trash/scenes/${encodeURIComponent(id)}/restore`),
  books: (pid: string) => call<TrashBook[]>("GET", `${proj(pid)}/trash/books`),
  restoreBook: (pid: string, id: string) =>
    call<ServerBook>("POST", `${proj(pid)}/trash/books/${encodeURIComponent(id)}/restore`),
}
