import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { studioApi, type LibraryItem, type StudioProject } from "./api"
import { latestOnly } from "./latestOnly"
import { PROJECT_KEY, pickProject } from "./libraryView"

function remembered(): string | null {
  try { return globalThis.localStorage?.getItem(PROJECT_KEY) ?? null } catch { return null }
}

/** Projekte des Nutzers + Bibliothek des gewählten Projekts (Etappe 1, nur lesen). */
export function useLibrary() {
  const { t } = useTranslation("studio")
  const [projects, setProjects] = useState<StudioProject[]>([])
  const [projectId, setProjectIdRaw] = useState("")
  const [items, setItems] = useState<LibraryItem[]>([])
  const [truncated, setTruncated] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [guard] = useState(latestOnly)

  useEffect(() => {
    let alive = true
    studioApi.projects()
      .then(({ projects }) => { if (alive) { setProjects(projects); setProjectIdRaw(pickProject(projects, remembered())) } })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : t("load_failed")) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [t])

  const load = useCallback(async (pid: string) => {
    if (!pid) { setItems([]); return }
    setLoading(true); setError(null)
    try {
      const r = await guard.run(pid, () => studioApi.library(pid))
      if (!r.current) return
      setItems(r.value.items); setTruncated(r.value.truncated); setLoading(false)
    } catch (e) {
      setItems([]); setError(e instanceof Error ? e.message : t("load_failed")); setLoading(false)
    }
  }, [t, guard])

  useEffect(() => {
    const first = window.setTimeout(() => { void load(projectId) }, 0)
    return () => window.clearTimeout(first)
  }, [projectId, load])

  const setProjectId = (pid: string) => {
    setProjectIdRaw(pid)
    try { globalThis.localStorage?.setItem(PROJECT_KEY, pid) } catch { /* nicht merken */ }
  }

  return { projects, projectId, setProjectId, items, truncated, loading, error, reload: () => load(projectId) }
}
