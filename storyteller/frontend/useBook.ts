// Zustand eines geöffneten Buchs für React: BookSync (Speichern mit Versionen) + Schnappschüsse
// vom Server + KI-Vorschläge dieser Sitzung.
import { useCallback, useEffect, useState } from "react"
import { BookSync, type SyncView } from "./bookSync"
import { updateScene, type Book, type Scene } from "./model"
import type { Versions } from "./serverBook"
import type { Suggestion } from "./suggest"
import { useSnapshots } from "./useSnapshots"

export type { Conflict, SaveState } from "./bookSync"

export function useBook(projectId: string, initial: Book, versions: Versions) {
  const [view, setView] = useState<SyncView>({ book: initial, saveState: "saved", saveError: "", conflict: null })
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  // Einmal je geöffnetem Buch (Workspace hat key=book.id); setView ist stabil.
  const [sync] = useState(() => new BookSync(projectId, initial, versions, setView))

  // Beim Verlassen: ausstehende Änderungen sofort senden; Seite schließen mit Ungespeichertem → Nachfrage.
  useEffect(() => {
    const onLeave = (e: BeforeUnloadEvent) => { if (sync.dirty) { void sync.flush(); e.preventDefault() } }
    window.addEventListener("beforeunload", onLeave)
    return () => { window.removeEventListener("beforeunload", onLeave); void sync.flush(); sync.dispose() }
  }, [sync])

  const change = useCallback((next: Book | ((b: Book) => Book)) => {
    sync.edit(typeof next === "function" ? next(sync.book) : next)
  }, [sync])

  const setScene = useCallback((sceneId: string, patch: Partial<Scene>) => {
    change((b) => updateScene(b, sceneId, patch))
  }, [change])

  const snaps = useSnapshots(projectId, initial.id, sync)

  const resolveConflict = useCallback(async (how: "reload" | "keep") => {
    const sceneId = await sync.resolve(how)
    if (sceneId) snaps.refresh(sceneId)
  }, [sync, snaps])

  const addSuggestion = useCallback((s: Suggestion) => {
    setSuggestions((all) => [s, ...all.map((x) => (x.sceneId === s.sceneId && x.state === "open" ? { ...x, state: "rejected" as const } : x))])
  }, [])

  const resolveSuggestion = useCallback((id: string, state: "accepted" | "rejected") => {
    setSuggestions((all) => all.map((x) => (x.id === id ? { ...x, state } : x)))
  }, [])

  return {
    projectId, book: view.book, saveState: view.saveState, saveError: view.saveError, conflict: view.conflict,
    change, setScene, resolveConflict,
    flush: useCallback(() => sync.flush(), [sync]),
    adoptStructure: useCallback((...a: Parameters<BookSync["adoptStructure"]>) => sync.adoptStructure(...a), [sync]),
    ...snaps,
    suggestions, addSuggestion, resolveSuggestion,
  }
}

export type BookState = ReturnType<typeof useBook>
