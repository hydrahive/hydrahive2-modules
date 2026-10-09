// A3 – Papierkorb (Spec nichts-geht-verloren.md §3), C1 – Kapitel löschen (Spec loeschen-c1.md): Aufrufe + reine Hilfen.
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

/** C1 – gelöschtes Kapitel (mit allen Szenen). */
export interface TrashChapter { id: string; chapter_id: string; title: string; scenes: number; words: number; deleted_at: string }
export interface RestoredChapter { placed: "original" | "end"; chapter_id: string; scenes: ServerScene[]; structure: ServerStructure }

/** Was beim Löschen einer Szene passiert (C1): letzte Szene eines Kapitels nimmt das Kapitel mit, letzte des Buchs bleibt. */
export function sceneDeleteKind(chaptersInBook: number, scenesInChapter: number): "scene" | "chapter" | "blocked" {
  if (scenesInChapter > 1) return "scene"
  return chaptersInBook > 1 ? "chapter" : "blocked"
}

/** Kapitel löschbar? Ein Buch behält immer mindestens ein Kapitel. */
export function canDeleteChapter(chaptersInBook: number): boolean {
  return chaptersInBook > 1
}

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
  chapters: (pid: string, bid: string) => call<TrashChapter[]>("GET", `${proj(pid)}/books/${encodeURIComponent(bid)}/trash/chapters`),
  restoreChapter: (pid: string, bid: string, id: string) =>
    call<RestoredChapter>("POST", `${proj(pid)}/books/${encodeURIComponent(bid)}/trash/chapters/${encodeURIComponent(id)}/restore`),
  deleteChapter: (pid: string, bid: string, cid: string) =>
    call<ServerStructure>("DELETE", `${proj(pid)}/books/${encodeURIComponent(bid)}/chapters/${encodeURIComponent(cid)}`),
  books: (pid: string) => call<TrashBook[]>("GET", `${proj(pid)}/trash/books`),
  restoreBook: (pid: string, id: string) =>
    call<ServerBook>("POST", `${proj(pid)}/trash/books/${encodeURIComponent(id)}/restore`),
}
