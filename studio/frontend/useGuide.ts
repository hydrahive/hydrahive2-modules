import { useCallback, useEffect, useState } from "react"
import { api } from "@/shared/api-client"
import { introOpen, rememberedWorkspace, rememberWorkspace, setIntroOpen, startWorkspace, type Overview } from "./guideLogic"
import type { Workspace } from "./workspaces"

/** Führung (B1): Übersicht des Projekts, Start-Reiter beim Öffnen/Projektwechsel, Reiter je Projekt merken, Kurzhilfe. */
export function useGuide(projectId: string, workspace: Workspace, setWorkspace: (w: Workspace) => void) {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [startedFor, setStartedFor] = useState("")
  const [intro, setIntro] = useState<Record<string, boolean>>({})

  const load = useCallback(async () => {
    if (!projectId) return null
    try {
      const o = await api.get<Overview>(`/modules/studio/projects/${encodeURIComponent(projectId)}/overview`)
      setOverview(o)
      return o
    } catch { return null }
  }, [projectId])

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

  const open = intro[workspace] ?? introOpen(workspace)
  return {
    overview: startedFor === projectId ? overview : null, reload: load, ready: startedFor === projectId,
    introOpen: open,
    toggleIntro: () => { setIntroOpen(workspace, !open); setIntro((x) => ({ ...x, [workspace]: !open })) },
  }
}
