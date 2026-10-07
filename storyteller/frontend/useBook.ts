// Zustand eines geöffneten Buchs für React: BookSync (Speichern mit Versionen) + Schnappschüsse
// vom Server + KI-Vorschläge dieser Sitzung.
import { useCallback, useEffect, useState } from "react"
import { BookSync, type SyncView } from "./bookSync"
import { findScene, originAfterEdit, updateScene, type Book, type Scene } from "./model"
import type { InfoProposal } from "./infoProposal"
import type { ProposalMark, Versions } from "./serverBook"
import type { Suggestion } from "./suggest"
import { useSnapshots } from "./useSnapshots"

export type { Conflict, SaveState } from "./bookSync"

interface OpenExtras { canWrite: boolean; proposals: Record<string, ProposalMark>; infoProposals?: Record<string, InfoProposal> }

export function useBook(projectId: string, initial: Book, versions: Versions,
  extras: OpenExtras = { canWrite: true, proposals: {} }) {
  const [view, setView] = useState<SyncView>({ book: initial, saveState: "saved", saveError: "", conflict: null, textRev: 0 })
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  // Abgelegte Ghostwriter-Vorschläge je Szene (aus dem Öffnen, ergänzt durch Läufe, entfernt beim Übernehmen/Verwerfen).
  const [proposals, setProposals] = useState<Record<string, ProposalMark>>(extras.proposals)
  // G4b: Vorschläge für Szenen-Infos (Titel/Zusammenfassung/Perspektive) je Szene.
  const [infoProposals, setInfoProposals] = useState<Record<string, InfoProposal>>(extras.infoProposals ?? {})
  const canWrite = extras.canWrite
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

  /** Text aus dem Editor (Mensch tippt): KI-Entwurf wird dabei „bearbeitet“ (wie auf dem Server). */
  const typeText = useCallback((sceneId: string, text: string) => {
    change((b) => {
      const s = findScene(b, sceneId)?.scene
      if (!s || s.text === text) return b
      return updateScene(b, sceneId, { text, origin: originAfterEdit(s.origin) })
    })
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
    projectId, book: view.book, saveState: view.saveState, saveError: view.saveError, conflict: view.conflict, textRev: view.textRev,
    change, setScene, typeText, resolveConflict,
    flush: useCallback(() => sync.flush(), [sync]),
    adoptStructure: useCallback((...a: Parameters<BookSync["adoptStructure"]>) => sync.adoptStructure(...a), [sync]),
    adoptScene: useCallback((s: Parameters<BookSync["adoptScene"]>[0]) => sync.adoptScene(s), [sync]),
    sceneVersion: useCallback((id: string) => sync.sceneVersion(id), [sync]),
    structureVersion: useCallback(() => sync.structureVersion(), [sync]),
    reloadText: useCallback(() => sync.reloadText(), [sync]),
    replaceSceneText: useCallback((id: string, text: string, origin?: Scene["origin"]) => sync.replaceText(id, text, origin), [sync]),
    ...snaps,
    suggestions, addSuggestion, resolveSuggestion,
    canWrite, proposals,
    markProposals: useCallback((ids: Record<string, ProposalMark>) => setProposals((p) => ({ ...p, ...ids })), []),
    clearProposal: useCallback((id: string) => setProposals((p) => {
      const { [id]: _gone, ...rest } = p
      return rest
    }), []),
    infoProposals,
    /** Nachfragen: der Server-Stand ersetzt die Liste (verworfene/übernommene verschwinden). */
    setInfoProposals,
    clearInfoProposal: useCallback((id: string) => setInfoProposals((p) => {
      const { [id]: _gone, ...rest } = p
      return rest
    }), []),
  }
}

export type BookState = ReturnType<typeof useBook>
