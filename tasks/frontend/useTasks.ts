import { useCallback, useEffect, useMemo, useState } from "react"
import { tasksApi } from "./api"
import { mergeSorted } from "./foreign"
import { isForeign, type AnyTask, type Task, type TaskStatus, type TaskPriority } from "./types"

interface UseTasksOptions {
  status?: TaskStatus
  projectId?: string
  /** Poll interval in ms when panel is visible. Default: 5000 */
  pollMs?: number
  /** Fremde Tasks anderer Instanzen mitladen (Gemeinsame Taskpflege). Standard: nein. */
  includeForeign?: boolean
  /** Projekt, auf dessen Zuordnung die fremden Tasks beschränkt werden (Reiter im Projekt). */
  foreignProjectId?: string | null
}

/** Fremde Tasks laden; bei Fehler leer, damit die eigenen sichtbar bleiben. */
export async function loadForeign(status: TaskStatus | undefined, projectId: string | null): Promise<AnyTask[]> {
  try {
    const rows = await tasksApi.list({ status, project_id: projectId ?? undefined, include_foreign: true })
    return rows.filter(isForeign)
  } catch {
    return []
  }
}

export function useTasks(opts: UseTasksOptions = {}) {
  const { status, projectId, pollMs = 5000, includeForeign = false, foreignProjectId = null } = opts
  const [all, setAll] = useState<AnyTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const own = await tasksApi.list({ status, project_id: projectId })
      // Fremde nur, wenn gewünscht; im Projekt auf dessen Zuordnung beschränkt (foreignProjectId).
      // Scheitert nur dieser Teil, bleiben die eigenen Tasks sichtbar (Review #456).
      const foreign = includeForeign ? await loadForeign(status, foreignProjectId) : []
      setAll(foreign.length ? mergeSorted(own, foreign) : own)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "")
    } finally {
      setLoading(false)
    }
  }, [status, projectId, includeForeign, foreignProjectId])

  useEffect(() => {
    load()
    const timer = setInterval(load, pollMs)
    const onVisible = () => { if (!document.hidden) load() }
    document.addEventListener("visibilitychange", onVisible)
    return () => {
      clearInterval(timer)
      document.removeEventListener("visibilitychange", onVisible)
    }
  }, [load, pollMs])

  const complete = useCallback(async (taskId: string) => {
    await tasksApi.update(taskId, { status: "done" })
    setAll((prev) => prev.map((t) => !isForeign(t) && t.id === taskId ? { ...t, status: "done" } : t))
  }, [])

  const updateTask = useCallback(async (taskId: string, data: {
    title?: string
    description?: string
    status?: TaskStatus
    priority?: TaskPriority
  }) => {
    const updated = await tasksApi.update(taskId, data)
    setAll((prev) => prev.map((t) => !isForeign(t) && t.id === taskId ? updated : t))
    return updated
  }, [])

  const deleteTask = useCallback(async (taskId: string) => {
    await tasksApi.delete(taskId)
    setAll((prev) => prev.filter((t) => isForeign(t) || t.id !== taskId))
  }, [])

  const createTask = useCallback(async (data: {
    title: string
    description?: string
    priority?: TaskPriority
    project_id?: string
  }) => {
    const created = await tasksApi.create(data)
    setAll((prev) => [created, ...prev])
    return created
  }, [])

  // tasks: nur eigene (Buddy-Box, Zähler); items: eigene und fremde zusammen (TaskPanel).
  const tasks = useMemo(() => all.filter((t): t is Task => !isForeign(t)), [all])
  return { tasks, items: all, loading, error, refresh: load, complete, updateTask, deleteTask, createTask }
}
