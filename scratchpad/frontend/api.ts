import { api } from "@/shared/api-client"
import type { Idea, IdeaChanges, IdeaListItem, IdeaMeta, StatusCounts } from "./types"

const BASE = "/modules/scratchpad"

export interface IdeaListResponse {
  ideas: IdeaListItem[]
  counts: StatusCounts
}

export const ideasApi = {
  meta: () => api.get<IdeaMeta>(`${BASE}/meta`),
  /** Alle Ideen des Nutzers. Gefiltert und gezählt wird in der Oberfläche (ideaView.ts). */
  list: () => api.get<IdeaListResponse>(`${BASE}/ideas`),
  get: (id: string) => api.get<Idea>(`${BASE}/ideas/${encodeURIComponent(id)}`),
  create: (data: { title: string; body: string; project_id: string | null }) =>
    api.post<Idea>(`${BASE}/ideas`, data),
  update: (id: string, changes: IdeaChanges) =>
    api.patch<Idea>(`${BASE}/ideas/${encodeURIComponent(id)}`, changes),
  /** Aus der Idee einen Task machen. Liefert die Idee mit Task-Verweis und neuem Status. */
  createTask: (id: string) => api.post<Idea>(`${BASE}/ideas/${encodeURIComponent(id)}/task`, {}),
  remove: (id: string) => api.delete<{ removed: boolean }>(`${BASE}/ideas/${encodeURIComponent(id)}`),
  removeNote: (id: string, noteId: number) =>
    api.delete<{ removed: boolean }>(`${BASE}/ideas/${encodeURIComponent(id)}/notes/${noteId}`),
}
