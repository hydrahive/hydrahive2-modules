// Ablauf „Szene schreiben“: Schätzung → Start → Live-Text → fertig (Vorschlag) → Annehmen/Ablehnen.
// Die Regeln fürs Annehmen (Schnappschuss, Herkunft, Gedächtnis) stehen in ghostAccept.ts.
import { useCallback, useEffect, useRef, useState } from "react"
import { storyApi, StoryApiError, type GhostEstimate } from "./api"
import { acceptGhostText } from "./ghostAccept"
import { streamGhostScene, type GhostDone } from "./ghostStream"
import type { Scene } from "./model"
import type { BookState } from "./useBook"

export type GhostPhase = "idle" | "running" | "ready" | "accepted"

export function useGhostScene(state: BookState, scene: Scene, lengthWords: number) {
  const [phase, setPhase] = useState<GhostPhase>("idle")
  const [text, setText] = useState("")
  const [done, setDone] = useState<GhostDone | null>(null)
  const [error, setError] = useState<StoryApiError | null>(null)
  const [estimate, setEstimate] = useState<GhostEstimate | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const textRef = useRef("")   // aktueller Stand für den Abbruch-Fall (State im Callback wäre veraltet)
  const { projectId, book } = state
  const canEstimate = !!scene.summary.trim() && lengthWords > 0

  // Schätzung nach Änderung von Länge/Modell neu holen (leicht verzögert, damit Tippen nicht spammt).
  useEffect(() => {
    if (!canEstimate) return
    let alive = true
    const timer = setTimeout(() => {
      storyApi.ghostEstimate(projectId, book.id, scene.id, lengthWords)
        .then((e) => { if (alive) setEstimate(e) })
        .catch(() => { if (alive) setEstimate(null) })
    }, 400)
    return () => { alive = false; clearTimeout(timer) }
  }, [projectId, book.id, scene.id, lengthWords, book.ghost.model, book.model, canEstimate])

  // Szene/Buch verlassen oder Komponente weg → laufenden Stream abbrechen.
  useEffect(() => () => abortRef.current?.abort(), [])

  const start = useCallback(async () => {
    setError(null)
    setText("")
    textRef.current = ""
    setDone(null)
    setPhase("running")
    await state.flush()   // Zusammenfassung/Steckbriefe müssen auf dem Server sein
    const ctrl = new AbortController()
    abortRef.current = ctrl
    try {
      const d = await streamGhostScene(projectId, book.id, { scene_id: scene.id, length_words: lengthWords },
        (t) => { textRef.current += t; setText(textRef.current) }, ctrl.signal)
      setDone(d)
      setPhase("ready")
    } catch (e) {
      const err = e instanceof StoryApiError ? e : new StoryApiError(0, "llm_failed", undefined, String(e))
      if (err.code !== "aborted") setError(err)
      // Abgebrochen mit schon geschriebenem Text → bleibt als Vorschlag stehen (Annehmen/Ablehnen).
      setPhase(err.code === "aborted" && textRef.current.trim() ? "ready" : "idle")
    } finally {
      abortRef.current = null
    }
  }, [state, projectId, book.id, scene.id, lengthWords])

  const stop = useCallback(() => abortRef.current?.abort(), [])

  const accept = useCallback(async () => {
    const r = await acceptGhostText(textRef.current, scene, {
      snapshot: state.snapshot,
      replace: state.replaceSceneText,
      remember: async (id) => {
        await state.flush()
        state.adoptScene((await storyApi.ghostSummarize(projectId, book.id, id)).scene)
      },
    })
    if (r === "snapshot_failed") setError(new StoryApiError(0, "snapshot_failed"))
    if (r === "accepted") setPhase("accepted")
  }, [scene, state, projectId, book.id])

  const reject = useCallback(() => { setText(""); setDone(null); setPhase("idle") }, [])

  return { phase, text, done, error, estimate: canEstimate ? estimate : null, start, stop, accept, reject }
}
