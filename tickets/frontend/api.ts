import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { Team, Ticket, TicketAttachment, TicketComment, TicketNotification } from "./types"

const BASE = "/modules/tickets"

export interface TicketFilters {
  status?: string
  priority?: string
  team_id?: string
  assigned_to?: string
  project_id?: string
  query?: string
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
  create: (payload: Partial<Ticket> & { title: string }) => api.post<Ticket>(`${BASE}/tickets`, payload),
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
  addMember: (teamId: string, userId: string, role: "member" | "lead" = "member") => api.post(`${BASE}/teams/${teamId}/members`, { user_id: userId, role }),
  removeMember: (teamId: string, userId: string) => api.delete(`${BASE}/teams/${teamId}/members/${userId}`),
  notifications: () => api.get<TicketNotification[]>(`${BASE}/notifications`),
  readNotification: (id: string) => api.post<{ read: boolean }>(`${BASE}/notifications/${id}/read`, {}),
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
