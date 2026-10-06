// Bücher aus dem klickbaren Entwurf 0.1.0 lagen im Browser (localStorage, je Projekt).
// Ab 0.2.0 liegen Bücher im Projektordner. Diese Datei liest die alten Bücher nur noch, damit sie
// übernommen werden können (Spec 1b §7), und löscht sie erst, wenn der Server sie bestätigt hat.
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

/** Alte Bücher haben kein `model`; fehlende Felder auffüllen, damit der Import sauber ist. */
function normalize(b: Book): Book {
  return { ...b, model: typeof b.model === "string" ? b.model : "", notes: b.notes ?? "", audience: b.audience ?? "", idea: b.idea ?? "" }
}

export const draftStore = {
  list(projectId: string): Book[] {
    return read(projectId).books.map(normalize)
  },
  /** Übernommene Bücher entfernen; alles andere bleibt. Gibt false zurück, wenn das Schreiben scheitert. */
  forget(projectId: string, bookIds: string[]): boolean {
    const data = read(projectId)
    data.books = data.books.filter((b) => !bookIds.includes(b.id))
    try {
      if (data.books.length === 0) localStorage.removeItem(KEY(projectId))
      else localStorage.setItem(KEY(projectId), JSON.stringify({ books: data.books }))
      return true
    } catch {
      return false
    }
  },
}
