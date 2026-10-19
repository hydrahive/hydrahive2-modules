import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { DEFAULT_PRESET, type Preset } from "./deliverLogic"
import { latestOnly } from "./latestOnly"
import { planApi, type Job } from "./planApi"
import { queueJobs, startedNotice } from "./queueLogic"
import { renderApi, type RenderItem } from "./renderApi"
import { translateApi } from "./translateLogic"
import type { PlanState } from "./usePlan"

const POLL_MS = 1500

/** Reiter „Ausgabe“ (4d, 7c): fertige Filme laden, Filme in die Warteschlange stellen, abbrechen, Fortschritt beobachten. */
export function useDeliver(p: PlanState, projectId: string, active: boolean, jobs: Job[], reloadJobs: () => void, onDone: () => void) {
  const { t } = useTranslation("studio")
  const [renders, setRenders] = useState<RenderItem[] | null>(null)                 // null = noch nicht geladen
  const [loadedFor, setLoadedFor] = useState("")
  const [guard] = useState(latestOnly)
  const queue = queueJobs(jobs)
  const running = queue.some((j) => j.status === "running" || j.status === "queued")
  const [cancelling, setCancelling] = useState<string | null>(null)
  const doneKey = jobs.filter((j) => j.kind === "render" && j.status === "done").map((j) => j.id).join("|")   // alle, nicht nur die gezeigten
  const [subLangs, setSubLangs] = useState<string[]>([])                           // Sprachen mit Untertiteln (6c)
  const [withSubs, setWithSubs] = useState(false)
  const notice = useRef("")
  const [preset, setPreset] = useState<Preset>(DEFAULT_PRESET)                     // Vorlage (7b), startet immer beim Standard

  const load = useCallback(async () => {
    if (!projectId) { setRenders([]); return }
    try {
      const r = await guard.run(projectId, () => renderApi.list(projectId))
      if (r.current) { setRenders(r.value.renders); setLoadedFor(projectId) }
    } catch { setRenders([]) }
  }, [projectId, guard])

  useEffect(() => {
    if (!active) return
    const id = window.setTimeout(() => {
      void load(); reloadJobs()
      translateApi.languages(projectId).then((l) => setSubLangs(l.languages.filter((x) => x.count > 0).map((x) => x.language)), () => setSubLangs([]))
    }, 0)
    return () => window.clearTimeout(id)
  }, [active, load, reloadJobs, projectId])

  // Fortschritt öfter nachfragen als die allgemeinen Aufträge; am Ende Liste neu laden
  useEffect(() => {
    if (!active || !running) return
    const id = window.setInterval(reloadJobs, POLL_MS)
    return () => window.clearInterval(id)
  }, [active, running, reloadJobs])
  // Jeder fertige Film → Liste neu laden (auch wenn weitere noch warten)
  const seenDone = useRef<string | null>(null)
  useEffect(() => {
    if (seenDone.current !== null && doneKey !== seenDone.current) {
      const id = window.setTimeout(() => { void load(); onDone() }, 0)
      seenDone.current = doneKey
      return () => window.clearTimeout(id)
    }
    seenDone.current = doneKey
  }, [doneKey, load, onDone])

  return {
    reload: load,
    renders: loadedFor === projectId ? renders : null, queue,                     // anderes Projekt → erst laden
    start: () => p.act(() => renderApi.start(projectId, { ...preset, subtitles: withSubs && subLangs.length > 0 }),
      () => notice.current, (r) => { notice.current = startedNotice(t, r as { status?: string; position?: number }); reloadJobs() }),
    cancelling,
    cancel: (id: string) => {
      setCancelling(id)
      void p.act(() => planApi.cancelJob(projectId, id), t("notice_render_cancelling"), () => reloadJobs())
        .finally(() => setCancelling(null))
    },
    subtitleLanguages: subLangs, withSubtitles: withSubs, setWithSubtitles: setWithSubs, preset, setPreset,
  }
}
