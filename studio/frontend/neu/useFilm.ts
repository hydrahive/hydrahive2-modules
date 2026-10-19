/** G5: „Film erzeugen“ – ein Auftrag, Fortschritt, Hand-Schnitt-Rückfrage, Liste der Filme. */
import { useCallback, useEffect, useState } from "react"
import { api } from "@/shared/api-client"
import { planApi, type Job } from "../planApi"
import { errorCode } from "../planLogic"
import { renderApi, type RenderItem } from "../renderApi"
import { useJobs } from "../useJobs"
import { filmBody, filmCosts, type FilmExtras } from "./guidedLogic"
import type { GuidedState } from "./useGuided"

export function useFilm(g: GuidedState, active: boolean) {
  const [films, setFilms] = useState<RenderItem[]>([])
  const [extras, setExtras] = useState<FilmExtras>({ music: true, voice: false, subtitles: false })
  const [asking, setAsking] = useState(false)
  const loadFilms = useCallback(async () => {
    if (!g.pid) { setFilms([]); return }
    try { setFilms((await renderApi.list(g.pid)).renders) } catch { /* Liste bleibt */ }
  }, [g.pid])
  const js = useJobs(g.pid, active, () => { void loadFilms(); void g.reload() })
  useEffect(() => { const h = window.setTimeout(() => { void loadFilms() }, 0); return () => window.clearTimeout(h) }, [loadFilms])
  const job: Job | null = js.jobs.find((j) => j.kind === "film") ?? null

  const make = async (rebuild?: boolean) => {
    setAsking(false)
    await g.run(async () => {
      try {
        await api.post<Job>(`/modules/studio/projects/${encodeURIComponent(g.pid)}/film`, filmBody(extras, rebuild))
      } catch (e) {
        if (errorCode(e) === "studio_film_edited") { setAsking(true); return }
        throw e
      }
    })
    await js.reload()
  }
  const stop = async () => { if (job) { await g.run(() => planApi.cancelJob(g.pid, job.id)); await js.reload() } }

  return { films, job, extras, setExtras, asking, setAsking, make, stop, costs: filmCosts(g.plan, extras) }
}

export type FilmActions = ReturnType<typeof useFilm>
