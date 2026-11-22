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

/** Das Blueprint-Board zur Idee. missing: gelöscht, fremd oder Blueprint-Modul fehlt. */
export interface IdeaBoardRef {
  id: number
  name: string | null
  has_proposal: boolean
  missing: boolean
}

export interface Idea extends IdeaBase {
  body: string
  notes: IdeaNote[]
  task: IdeaTaskRef | null
  board: IdeaBoardRef | null
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

/** Idee einer anderen Instanz (Gemeinsame Taskpflege, Spec federation-shared-tasks.md). Nur lesen. */
export interface ForeignIdea {
  foreign: true
  origin_fp: string
  origin_name: string | null
  item_id: string
  owner: string
  title: string
  status: IdeaStatus
  /** Ursprungsprojekt beim Ursprung (nicht die eigene ID). */
  project_id: string | null
  project_name: string | null
  /** Eigenes Projekt nach Zuordnung oder null. */
  local_project_id: string | null
  created_at: string
  updated_at: string
  origin_last_seen: string | null
  stale: boolean
}

/** Volltext einer fremden Idee (GET /ideas/foreign/{origin_fp}/{item_id}). */
export interface ForeignIdeaFull {
  item: Partial<ForeignIdea>
  content: { body?: string; notes?: Array<Pick<IdeaNote, "author" | "agent_name" | "body" | "created_at">> } | null
  source: "live" | "snapshot" | "none" | "metadata"
  origin_offline: boolean
  snapshot_at: string | null
  last_seen: string | null
  hub_unreachable: boolean
}
