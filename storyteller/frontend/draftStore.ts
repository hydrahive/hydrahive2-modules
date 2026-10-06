// Ablage im ENTWURF: Bücher liegen im Browser (localStorage), getrennt je Projekt.
// Spec §8 sieht Dateien im Projekt-Workspace vor – das ersetzt diese Datei im Ausbau,
// die Oberfläche bleibt gleich (gleiche Funktionen: list/get/save/remove).
import type { Book } from "./model"

const KEY = (projectId: string) => `storyteller.draft.v1.${projectId}`

interface Stored { books: Book[]; last?: { bookId: string; sceneId: string } }

function read(projectId: string): Stored {
  try {
    const raw = localStorage.getItem(KEY(projectId))
    const data = raw ? (JSON.parse(raw) as Stored) : null
    return data && Array.isArray(data.books) ? data : { books: [] }
  } catch {
    return { books: [] }
  }
}

/** false = Speichern fehlgeschlagen (z. B. Speicher voll). Die Oberfläche zeigt das rot an. */
function write(projectId: string, data: Stored): boolean {
  try {
    localStorage.setItem(KEY(projectId), JSON.stringify(data))
    return true
  } catch {
    return false
  }
}

export const draftStore = {
  list(projectId: string): Book[] {
    return [...read(projectId).books].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
  },
  get(projectId: string, bookId: string): Book | null {
    return read(projectId).books.find((b) => b.id === bookId) ?? null
  },
  save(projectId: string, book: Book): boolean {
    const data = read(projectId)
    const stamped = { ...book, updatedAt: new Date().toISOString() }
    const i = data.books.findIndex((b) => b.id === book.id)
    if (i >= 0) data.books[i] = stamped
    else data.books.push(stamped)
    return write(projectId, data)
  },
  remove(projectId: string, bookId: string): boolean {
    const data = read(projectId)
    data.books = data.books.filter((b) => b.id !== bookId)
    if (data.last?.bookId === bookId) delete data.last
    return write(projectId, data)
  },
  last(projectId: string): { bookId: string; sceneId: string } | undefined {
    return read(projectId).last
  },
  setLast(projectId: string, bookId: string, sceneId: string): void {
    const data = read(projectId)
    data.last = { bookId, sceneId }
    write(projectId, data)
  },
}
