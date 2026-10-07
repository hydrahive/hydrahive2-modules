// Ghostwriter G2 – Lauf eines Buchs verfolgen: alle 2 s abfragen, solange er läuft; fertig geschriebene
// Szenen nachladen (adoptScene), abgelegte Vorschläge an der Szene markieren. Der Lauf selbst läuft auf
// dem Server weiter, auch wenn das Buch geschlossen wird.
import { useCallback, useEffect, useRef, useState } from "react"
import { StoryApiError } from "./api"
import { runApi, type RunEstimate, type RunRequest } from "./runApi"
import { isFinished, scenesToReload, type RunInfo } from "./runView"
import type { BookState } from "./useBook"

const POLL_MS = 2000

export function useGhostRun(state: BookState) {
  const { projectId, book } = state
  const [run, setRun] = useState<RunInfo | null>(null)
  const [error, setError] = useState<StoryApiError | null>(null)
  const last = useRef<RunInfo | null>(null)

  const apply = useCallback(async (next: RunInfo | null) => {
    const prev = last.current
    last.current = next
    setRun(next)
    if (!next || !prev || prev.id !== next.id) return   // erstes Laden: nichts nachladen (Buch ist frisch)
    const { written, proposals } = scenesToReload(prev, next)
    for (const id of written) {
      try { state.adoptScene(await runApi.scene(projectId, book.id, id)) } catch { /* nächste Abfrage */ }
    }
    if (proposals.length) {
      const marks = Object.fromEntries(next.progress.filter((p) => proposals.includes(p.scene_id))
        .map((p) => [p.scene_id, { words: p.words ?? 0, model: next.model, at: "" }]))
      state.markProposals(marks)
    }
  }, [state, projectId, book.id])

  const refresh = useCallback(async () => {
    try { await apply(await runApi.get(projectId, book.id)) } catch (e) {
      if (e instanceof StoryApiError) setError(e)
    }
  }, [apply, projectId, book.id])

  // Beim Öffnen einmal holen (nach dem ersten Zeichnen); danach nur abfragen, solange ein Lauf aktiv ist.
  useEffect(() => {
    const first = setTimeout(() => { void refresh() }, 0)
    return () => clearTimeout(first)
  }, [refresh])
  const active = !isFinished(run)
  useEffect(() => {
    if (!active) return
    const timer = setInterval(() => { void refresh() }, POLL_MS)
    return () => clearInterval(timer)
  }, [active, refresh])

  const estimate = useCallback((r: RunRequest): Promise<RunEstimate> => runApi.estimate(projectId, book.id, r), [projectId, book.id])

  const start = useCallback(async (r: RunRequest, overLimit: boolean) => {
    setError(null)
    try {
      await state.flush()   // Zusammenfassungen müssen auf dem Server sein
      const started = await runApi.start(projectId, book.id, r, overLimit)
      last.current = { ...started, progress: started.progress.map((p) => ({ ...p, state: "waiting" as const })) }
      setRun(started)
      return true
    } catch (e) {
      setError(e instanceof StoryApiError ? e : new StoryApiError(0, "llm_failed", undefined, String(e)))
      return false
    }
  }, [state, projectId, book.id])

  const cancel = useCallback(async () => {
    try { await runApi.cancel(projectId, book.id) } finally { await refresh() }
  }, [projectId, book.id, refresh])

  return { run, active, error, estimate, start, cancel, refresh }
}
