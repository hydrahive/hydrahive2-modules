export type TaskStatus = "open" | "in_progress" | "done" | "cancelled"
export type TaskPriority = "low" | "medium" | "high"

export interface Task {
  id: string
  username: string
  project_id: string | null
  session_id: string | null
  title: string
  description: string
  status: TaskStatus
  priority: TaskPriority
  created_at: string
  updated_at: string
  /** Anzahl früherer Fassungen (Verlauf, Task df2f2eb2). Fehlt bei älteren Backends. */
  history_count?: number
  /** Herkunft, zum Beispiel "idea" und die ID der Idee. Fehlt bei Backends vor 1.3.0. */
  source_kind?: string | null
  source_id?: string | null
}

export interface TaskVersion {
  title: string
  description: string
  changed_at: string
  source: "update" | "restored"
}

/** Task einer anderen Instanz (Gemeinsame Taskpflege, Spec federation-shared-tasks.md). Nur lesen. */
export interface ForeignTask {
  foreign: true
  origin_fp: string
  origin_name: string | null
  kind: "task"
  item_id: string
  owner: string
  title: string
  status: TaskStatus
  priority: TaskPriority
  project_id: string | null
  project_name: string | null
  created_at: string
  updated_at: string
  origin_last_seen: string | null
  stale: boolean
  pending_edits: number
  local_project_id: string | null
}

export type AnyTask = Task | ForeignTask

export function isForeign(task: AnyTask): task is ForeignTask {
  return (task as ForeignTask).foreign === true
}

/** Volltext eines fremden Tasks (GET /tasks/foreign/{origin_fp}/{item_id}). */
export interface ForeignTaskFull {
  item: Partial<ForeignTask>
  content: { description?: string } | null
  source: "live" | "snapshot" | "none" | "metadata"
  origin_offline: boolean
  snapshot_at: string | null
  last_seen: string | null
  hub_unreachable: boolean
}
