export type TicketStatus = "open" | "triaged" | "in_progress" | "waiting" | "resolved" | "closed" | "cancelled"
export type TicketPriority = "low" | "normal" | "high" | "urgent"

export interface TicketComment {
  id: string
  ticket_id: string
  author_id: string
  author_kind: "user" | "agent"
  body: string
  created_at: string
}

export interface TicketAttachment {
  id: string
  ticket_id: string
  comment_id: string | null
  original_name: string
  storage_key?: string
  media_type: string
  size_bytes: number
  sha256?: string
  uploaded_by?: string
  created_at: string
}

export interface TicketEvent {
  id: string
  ticket_id: string
  actor_id: string
  actor_kind: "user" | "agent" | "system"
  event_type: string
  payload: Record<string, unknown>
  created_at: string
}

export interface Ticket {
  id: string
  number: number
  title: string
  description: string
  status: TicketStatus
  priority: TicketPriority
  category: string
  tags: string[]
  created_by: string
  assigned_to: string | null
  team_id: string | null
  project_id: string | null
  task_id: string | null
  session_id: string | null
  created_at: string
  updated_at: string
  resolved_at: string | null
  closed_at: string | null
  response_due_at: string | null
  resolution_due_at: string | null
  due_at: string | null
  manual_due_at: string | null
  due_at_source: "sla" | "manual" | "none"
  first_response_at: string | null
  comments?: TicketComment[]
  events?: TicketEvent[]
  attachments?: TicketAttachment[]
}

export interface TeamMember {
  team_id: string
  user_id: string
  role: "member" | "lead"
  created_at: string
}

export interface Team {
  id: string
  name: string
  description: string
  created_by: string
  created_at: string
  updated_at: string
  members: TeamMember[]
}

export interface TicketNotification {
  id: string
  user_id: string
  ticket_id: string
  kind: string
  read_at: string | null
  created_at: string
}
