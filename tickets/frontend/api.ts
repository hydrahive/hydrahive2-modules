import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { Team, TeamMember, Ticket, TicketAttachment, TicketComment, TicketNotification } from "./types"

export interface TicketDashboard {
  open: number
  triaged: number
  in_progress: number
  waiting: number
  resolved: number
  closed: number
  cancelled: number
  overdue: number
  due_soon: number
  unassigned: number
  mine: number
  team: number
  avg_first_response_seconds: number | null
  avg_resolution_seconds: number | null
}

export interface SavedView {
  id: string
  owner_id: string
  team_id: string | null
  name: string
  filters: TicketFilters
  sort: string
  direction: "asc" | "desc"
}

const BASE = "/modules/tickets"

export interface TicketFilters {
  status?: string
  priority?: string
  team_id?: string
  assigned_to?: string
  project_id?: string
  query?: string
  overdue?: boolean
  due_before?: string
  sort?: string
  direction?: "asc" | "desc"
  limit?: number
  offset?: number
}

function queryString(filters: TicketFilters) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value))
  }
  const query = params.toString()
  return query ? `?${query}` : ""
}

export const ticketsApi = {
  list: (filters: TicketFilters = {}) => api.get<Ticket[]>(`${BASE}/tickets${queryString(filters)}`),
  get: (id: string) => api.get<Ticket>(`${BASE}/tickets/${id}`),
  create: (payload: { title: string; description?: string; priority?: string; category?: string }) => api.post<Ticket>(`${BASE}/tickets`, payload),
  update: (id: string, payload: Partial<Ticket>) => api.patch<Ticket>(`${BASE}/tickets/${id}`, payload),
  comments: (id: string) => api.get<TicketComment[]>(`${BASE}/tickets/${id}/comments`),
  comment: (id: string, body: string) => api.post<TicketComment>(`${BASE}/tickets/${id}/comments`, { body }),
  attachments: (id: string) => api.get<TicketAttachment[]>(`${BASE}/tickets/${id}/attachments`),
  upload: (id: string, file: File) => {
    const form = new FormData()
    form.append("file", file)
    return api.postForm<TicketAttachment>(`${BASE}/tickets/${id}/attachments`, form)
  },
  teams: () => api.get<Team[]>(`${BASE}/teams`),
  createTeam: (name: string, description: string) => api.post<Team>(`${BASE}/teams`, { name, description }),
  updateTeam: (id: string, payload: { name?: string; description?: string }) => api.patch<Team>(`${BASE}/teams/${id}`, payload),
  addMember: (teamId: string, userId: string, role: "member" | "lead" = "member") => api.post<TeamMember>(`${BASE}/teams/${teamId}/members`, { user_id: userId, role }),
  removeMember: (teamId: string, userId: string) => api.delete<{ removed: boolean }>(`${BASE}/teams/${teamId}/members/${userId}`),
  notifications: () => api.get<TicketNotification[]>(`${BASE}/notifications`),
  readNotification: (id: string) => api.post<{ read: boolean }>(`${BASE}/notifications/${id}/read`, {}),
  dashboard: () => api.get<TicketDashboard>(`${BASE}/dashboard`),
  views: () => api.get<SavedView[]>(`${BASE}/saved-views`),
  createView: (payload: Pick<SavedView, "name" | "filters" | "sort" | "direction">) => api.post<SavedView>(`${BASE}/saved-views`, payload),
  deleteView: (id: string) => api.delete<void>(`${BASE}/saved-views/${id}`),
  bulkUpdate: (ticketIds: string[], update: Partial<Ticket>) => api.post(`${BASE}/bulk-update`, { ticket_ids: ticketIds, update }),
}

export async function downloadAttachment(ticketId: string, attachment: TicketAttachment) {
  const token = useAuthStore.getState().token
  const response = await fetch(`/api${BASE}/tickets/${ticketId}/attachments/${attachment.id}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) throw new Error("attachment_download_failed")
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = attachment.original_name
  anchor.click()
  URL.revokeObjectURL(url)
}
