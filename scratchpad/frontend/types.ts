export const STATUSES = ["new", "review", "planned", "parked", "done", "dropped"] as const
export type IdeaStatus = (typeof STATUSES)[number]
/** „Offen“ in Liste und Filter: alles, woran noch gearbeitet wird. */
export const OPEN_STATUSES: readonly IdeaStatus[] = ["new", "review", "planned"]

export type IdeaOrigin = "user" | "agent"
/** "all" = alle Projekte, "none" = ohne Projekt, sonst eine Projekt-ID. */
export type ProjectFilter = "all" | "none" | (string & {})
export type StatusFilter = "open" | "all" | IdeaStatus
export type StatusCounts = Record<IdeaStatus, number>

interface IdeaBase {
  id: string
  project_id: string | null
  title: string
  status: IdeaStatus
  origin: IdeaOrigin
  task_id: string | null
  board_id: number | null
  created_at: string
  updated_at: string
}

/** Zeile der Liste: ohne volle Beschreibung. */
export interface IdeaListItem extends IdeaBase {
  body_preview: string
  note_count: number
}

export interface IdeaNote {
  id: number
  idea_id: string
  author: "agent" | "system"
  agent_name: string | null
  body: string
  created_at: string
}

/** Der aus der Idee entstandene Task. missing: gelöscht, fremd oder Tasks-Modul fehlt. */
export interface IdeaTaskRef {
  id: string
  short_id: string
  title: string | null
  status: string | null
  missing: boolean
}

export interface Idea extends IdeaBase {
  body: string
  notes: IdeaNote[]
  task: IdeaTaskRef | null
}

export interface ProjectRef {
  id: string
  name: string
}

export interface IdeaMeta {
  statuses: IdeaStatus[]
  open_statuses: IdeaStatus[]
  tasks_installed: boolean
  blueprint_installed: boolean
  limits: { title: number; body: number; ideas: number }
}

export interface IdeaChanges {
  title?: string
  body?: string
  status?: IdeaStatus
  project_id?: string | null
}
