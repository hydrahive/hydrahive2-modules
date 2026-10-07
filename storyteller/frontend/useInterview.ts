// Ghostwriter G3 – Interview eines Kapitels für React: laden, Änderungen nach kurzer Pause speichern.
// Die Speicher-Regeln (Version, Konflikt, nichts verlieren) stecken in interviewSync.ts (getestet).
import { useCallback, useEffect, useRef, useState } from "react"
import { interviewApi } from "./interviewApi"
import type { Interview, Question } from "./interviewModel"
import { InterviewSync, type InterviewSaveState } from "./interviewSync"

const SAVE_MS = 800

export function useInterview(projectId: string, bookId: string, chapterId: string) {
  const [view, setView] = useState<{ questions: Question[]; state: InterviewSaveState | "loading"; conflict: Interview | null }>(
    { questions: [], state: "loading", conflict: null })
  const sync = useRef<InterviewSync | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const show = useCallback(() => {
    const s = sync.current
    if (s) setView({ questions: s.questions, state: s.state, conflict: s.conflict })
  }, [])

  useEffect(() => {
    let alive = true
    interviewApi.get(projectId, bookId, chapterId).then((x) => {
      if (!alive) return
      sync.current = new InterviewSync(x.version, (v, q) => interviewApi.save(projectId, bookId, chapterId, v, q), x.questions)
      show()
    }).catch(() => { if (alive) setView((v) => ({ ...v, state: "failed" })) })
    return () => { alive = false }
  }, [projectId, bookId, chapterId, show])

  const flush = useCallback(async () => {
    if (timer.current) { clearTimeout(timer.current); timer.current = null }
    await sync.current?.flush()
    show()
  }, [show])

  // Beim Verlassen des Kapitels ausstehende Änderungen sofort senden.
  useEffect(() => () => { void sync.current?.flush() }, [chapterId])

  const change = useCallback((next: Question[]) => {
    if (!sync.current) return
    sync.current.change(next)
    show()
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => { void flush() }, SAVE_MS)
  }, [flush, show])

  const resolve = useCallback(async (how: "reload" | "keep") => {
    await sync.current?.resolve(how)
    show()
  }, [show])

  return { questions: view.questions, state: view.state, conflict: view.conflict, change, flush, resolve, retry: flush }
}
