// Zustand eines geöffneten Buchs: Änderungen, Autosave (1 s), Schnappschüsse, KI-Vorschläge.
import { useCallback, useEffect, useRef, useState } from "react"
import { draftStore } from "./draftStore"
import { findScene, newId, updateScene, type Book, type Scene } from "./model"
import type { Suggestion } from "./suggest"

export type SaveState = "saved" | "saving" | "failed"
export interface Snapshot { id: string; sceneId: string; at: string; text: string }

const MAX_SNAPSHOTS = 50

export function useBook(projectId: string, initial: Book) {
  const [book, setBook] = useState<Book>(initial)
  const [saveState, setSaveState] = useState<SaveState>("saved")
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const latest = useRef(book)

  const flush = useCallback(() => {
    if (timer.current) { clearTimeout(timer.current); timer.current = null }
    setSaveState(draftStore.save(projectId, latest.current) ? "saved" : "failed")
  }, [projectId])

  /** Jede Änderung geht hier durch: sofort sichtbar, gespeichert 1 s nach der letzten. */
  const change = useCallback((next: Book | ((b: Book) => Book)) => {
    setBook((prev) => {
      const b = typeof next === "function" ? next(prev) : next
      latest.current = b
      return b
    })
    setSaveState("saving")
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(flush, 1000)
  }, [flush])

  // Beim Verlassen (Buchwechsel, Seite schließen) ausstehende Änderungen sofort sichern.
  useEffect(() => {
    const onLeave = () => { if (timer.current) flush() }
    window.addEventListener("beforeunload", onLeave)
    return () => { window.removeEventListener("beforeunload", onLeave); onLeave() }
  }, [flush])

  const setScene = useCallback((sceneId: string, patch: Partial<Scene>) => {
    change((b) => updateScene(b, sceneId, patch))
  }, [change])

  const snapshot = useCallback((sceneId: string) => {
    const s = findScene(latest.current, sceneId)?.scene
    if (!s) return
    setSnapshots((all) => {
      const mine = all.filter((x) => x.sceneId === sceneId)
      if (mine[0]?.text === s.text) return all  // nichts Neues
      const others = all.filter((x) => x.sceneId !== sceneId)
      const snap = { id: newId("snap"), sceneId, at: new Date().toISOString(), text: s.text }
      return [snap, ...mine].slice(0, MAX_SNAPSHOTS).concat(others)
    })
  }, [])

  const restore = useCallback((snap: Snapshot) => {
    snapshot(snap.sceneId)
    setScene(snap.sceneId, { text: snap.text })
  }, [snapshot, setScene])

  const addSuggestion = useCallback((s: Suggestion) => {
    setSuggestions((all) => [s, ...all.map((x) => (x.sceneId === s.sceneId && x.state === "open" ? { ...x, state: "rejected" as const } : x))])
  }, [])

  const resolveSuggestion = useCallback((id: string, state: "accepted" | "rejected") => {
    setSuggestions((all) => all.map((x) => (x.id === id ? { ...x, state } : x)))
  }, [])

  return {
    book, change, setScene, saveState, flush,
    snapshots, snapshot, restore,
    suggestions, addSuggestion, resolveSuggestion,
  }
}
