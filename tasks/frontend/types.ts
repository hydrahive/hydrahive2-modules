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
