import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { DEFAULT_PRESET, type Preset } from "./deliverLogic"
import { latestOnly } from "./latestOnly"
import type { Job } from "./planApi"
import { renderApi, type RenderItem } from "./renderApi"
import { translateApi } from "./translateLogic"
import type { PlanState } from "./usePlan"

const POLL_MS = 1500

/** Reiter „Ausgabe“ (4d): fertige Filme laden, Film starten, Fortschritt beobachten (solange der Reiter offen ist). */
export function useDeliver(p: PlanState, projectId: string, active: boolean, jobs: Job[], reloadJobs: () => void, onDone: () => void) {
  const { t } = useTranslation("studio")
  const [renders, setRenders] = useState<RenderItem[] | null>(null)                 // null = noch nicht geladen
  const [loadedFor, setLoadedFor] = useState("")
  const [guard] = useState(latestOnly)
  const job = jobs.find((j) => j.kind === "render") ?? null
  const running = job?.status === "running" || job?.status === "queued"
  const wasRunning = useRef(false)
  const [subLangs, setSubLangs] = useState<string[]>([])                           // Sprachen mit Untertiteln (6c)
  const [withSubs, setWithSubs] = useState(false)
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
  useEffect(() => {
    if (wasRunning.current && !running) {
      const id = window.setTimeout(() => { void load(); onDone() }, 0)
      wasRunning.current = running
      return () => window.clearTimeout(id)
    }
    wasRunning.current = running
  }, [running, load, onDone])

  return {
    renders: loadedFor === projectId ? renders : null, job,                      // anderes Projekt → erst laden
    start: () => p.act(() => renderApi.start(projectId, { ...preset, subtitles: withSubs && subLangs.length > 0 }), t("notice_render_started"), () => reloadJobs()),
    subtitleLanguages: subLangs, withSubtitles: withSubs, setWithSubtitles: setWithSubs, preset, setPreset,
  }
}
