// T1c (Spec schreib-team.md §4): Buch als eigenes Projekt mit Schreib-Team anlegen. Rein, ohne React → testbar.
import { call, StoryApiError } from "./api"
import type { ServerBook } from "./api"
import type { BookKind } from "./model"

/** Wohin das neue Buch kommt: eigenes Projekt (mit Autor + Helfern) oder das gerade gewählte Projekt. */
export type BookPlace = "own" | "current"

export function placesFor(canCreate: boolean, hasCurrent = true): BookPlace[] {
  return [...(canCreate ? ["own" as const] : []), ...(hasCurrent ? ["current" as const] : [])]
}

export function defaultPlace(canCreate: boolean, hasCurrent = true): BookPlace {
  return placesFor(canCreate, hasCurrent)[0] ?? "current"
}

export interface BookProjectCreated {
  project_id: string
  book: Pick<ServerBook, "id"> & Partial<ServerBook>
  team?: { author: string; helpers: Record<string, string> }
}

export function afterCreate(out: BookProjectCreated): { projectId: string; bookId: string } {
  return { projectId: out.project_id, bookId: out.book.id }
}

/** Projekt wurde vom Storyteller für genau ein Buch angelegt (metadata.storyteller). */
export function isBookProject(p: { metadata?: Record<string, unknown> }): boolean {
  const st = p.metadata?.storyteller
  return typeof st === "object" && st !== null && "book_id" in st
}

type T = (key: string, opts?: { defaultValue?: string }) => string

/** Fehler für die Anzeige: bekannter Code (texts: err_<code>) als Text, sonst die Meldung. */
export function errorText(t: T, e: unknown): string {
  if (e instanceof StoryApiError) return t(`err_${e.code}`, { defaultValue: e.message || e.code })
  return e instanceof Error ? e.message : String(e)
}

export interface BookProjectFields { title: string; kind: BookKind; language: string; audience: string; idea: string; model?: string }

/** T1f: „In eigenes Projekt umziehen“ – nur mit Recht zum Anlegen und nur, wenn das Buch noch in einem normalen
 *  Projekt liegt (Server meldet is_book_project; fehlt das Feld, ist der Server zu alt → kein Knopf). */
export function canMove(canCreate: boolean, book: { is_book_project?: boolean }): boolean {
  return canCreate && book.is_book_project === false
}

export interface BookMoved { project_id: string; book_id: string; backup: string }

export function afterMove(out: BookMoved): { projectId: string; bookId: string } {
  return { projectId: out.project_id, bookId: out.book_id }
}

export const bookProjectApi = {
  canCreate: () => call<{ can_create: boolean }>("GET", "/book-projects/can-create"),
  create: (f: BookProjectFields) => call<BookProjectCreated>("POST", "/book-projects", f),
  move: (projectId: string, bookId: string) => call<BookMoved>(
    "POST", `/projects/${encodeURIComponent(projectId)}/books/${encodeURIComponent(bookId)}/move-to-own-project`),
}
