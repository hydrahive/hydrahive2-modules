import { useCallback, useEffect, useState } from "react"
import { api } from "@/shared/api-client"
import { latestOnly } from "./latestOnly"
import { introOpen, rememberedWorkspace, rememberWorkspace, setIntroOpen, startWorkspace, type Overview } from "./guideLogic"
import type { Workspace } from "./workspaces"

/** Führung (B1): Übersicht des Projekts, Start-Reiter beim Öffnen/Projektwechsel, Reiter je Projekt merken, Kurzhilfe. */
export function useGuide(projectId: string, workspace: Workspace, setWorkspace: (w: Workspace) => void,
  /** ändert sich, sobald Drehbuch oder Schnittfassung neu geladen wurden → Fortschritt neu holen */
  changed: unknown = null) {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [startedFor, setStartedFor] = useState("")
  const [intro, setIntro] = useState<Record<string, boolean>>({})
  const [guard] = useState(latestOnly)

  const load = useCallback(async () => {
    if (!projectId) return null
    try {
      const r = await guard.run(projectId, () => api.get<Overview>(`/modules/studio/projects/${encodeURIComponent(projectId)}/overview`))
      if (!r.current) return null
      setOverview(r.value)
      return r.value
    } catch { return null }
  }, [projectId, guard])

  // Beim Öffnen und bei jedem Projektwechsel einmal den passenden Reiter wählen
  useEffect(() => {
    if (!projectId || startedFor === projectId) return
    let alive = true
    const id = window.setTimeout(() => {
      void load().then((o) => {
        if (!alive) return
        setStartedFor(projectId)
        setWorkspace(startWorkspace(o, rememberedWorkspace(projectId)))
      })
    }, 0)
    return () => { alive = false; window.clearTimeout(id) }
  }, [projectId, startedFor, load, setWorkspace])

  useEffect(() => { if (projectId && startedFor === projectId) rememberWorkspace(projectId, workspace) }, [projectId, startedFor, workspace])

  useEffect(() => {
    if (!projectId || startedFor !== projectId) return
    const id = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(id)
  }, [changed, projectId, startedFor, load])

  const open = intro[workspace] ?? introOpen(workspace)
  return {
    overview: startedFor === projectId ? overview : null, reload: load, ready: startedFor === projectId,
    introOpen: open,
    toggleIntro: () => { setIntroOpen(workspace, !open); setIntro((x) => ({ ...x, [workspace]: !open })) },
  }
}
