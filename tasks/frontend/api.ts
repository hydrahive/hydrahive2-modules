import { api } from "@/shared/api-client"
import type { AnyTask, ForeignTaskFull, Task, TaskStatus, TaskPriority, TaskVersion } from "./types"

const BASE = "/modules/tasks/tasks"

export const tasksApi = {
  list(params?: { status?: TaskStatus; project_id?: string; include_foreign?: boolean }): Promise<AnyTask[]> {
    const qs = new URLSearchParams()
    if (params?.status) qs.set("status", params.status)
    if (params?.project_id) qs.set("project_id", params.project_id)
    if (params?.include_foreign) qs.set("include_foreign", "1")
    const q = qs.toString()
    return api.get<AnyTask[]>(`${BASE}${q ? `?${q}` : ""}`)
  },

  /** Volltext eines fremden Tasks über den Hub (Gemeinsame Taskpflege). */
  foreign(originFp: string, itemId: string): Promise<ForeignTaskFull> {
    return api.get<ForeignTaskFull>(`${BASE}/foreign/${encodeURIComponent(originFp)}/${encodeURIComponent(itemId)}`)
  },

  create(data: {
    title: string
    description?: string
    priority?: TaskPriority
    project_id?: string
    session_id?: string
  }): Promise<Task> {
    return api.post<Task>(BASE, data)
  },

  update(taskId: string, data: {
    title?: string
    description?: string
    status?: TaskStatus
    priority?: TaskPriority
    note?: string
  }): Promise<Task> {
    return api.patch<Task>(`${BASE}/${taskId}`, data)
  },

  history(taskId: string): Promise<TaskVersion[]> {
    return api.get<TaskVersion[]>(`${BASE}/${taskId}/history`)
  },

  delete(taskId: string): Promise<void> {
    return api.delete(`${BASE}/${taskId}`)
  },
}
