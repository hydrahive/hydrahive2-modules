import { useCallback, useEffect, useRef, useState } from "react"
import { planApi, type Job } from "./planApi"
import { runningJobs } from "./jobLogic"

const POLL_MS = 3000

/** Aufträge des Projekts. Fragt alle 3 s nach, solange einer läuft; meldet, wenn einer fertig wurde (→ neu laden). */
export function useJobs(projectId: string, active: boolean, onFinished: () => void) {
  const [jobs, setJobs] = useState<Job[]>([])
  const before = useRef<Set<string>>(new Set())
  const steps = useRef("")
  const finished = useRef(onFinished)
  useEffect(() => { finished.current = onFinished }, [onFinished])

  const load = useCallback(async () => {
    if (!projectId) { setJobs([]); return }
    try {
      const list = (await planApi.jobs(projectId)).jobs
      const nowRunning = new Set(list.filter((j) => j.status === "running" || j.status === "queued").map((j) => j.id))
      // Sammelaufträge machen nach jedem Schritt etwas fertig → dann auch neu laden, nicht erst am Ende
      const stepKey = list.filter((j) => j.progress && nowRunning.has(j.id)).map((j) => `${j.id}:${j.progress?.done}:${j.progress?.failed}`).join("|")
      const ended = [...before.current].some((id) => !nowRunning.has(id)) || (stepKey !== steps.current && steps.current !== "")
      steps.current = stepKey
      before.current = nowRunning
      setJobs(list)
      if (ended) finished.current()
    } catch { /* nächster Versuch beim nächsten Takt */ }
  }, [projectId])

  useEffect(() => {
    if (!active) return
    const first = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(first)
  }, [active, load])

  const running = runningJobs(jobs)
  useEffect(() => {
    if (!active || running === 0) return
    const id = window.setInterval(() => { void load() }, POLL_MS)
    return () => window.clearInterval(id)
  }, [active, running, load])

  return { jobs, running, reload: load }
}
