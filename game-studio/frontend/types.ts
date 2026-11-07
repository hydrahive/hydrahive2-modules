export type EntryKind = "new" | "adopt" | "archive"
export type TargetPlatform = "desktop" | "web" | "mobile"
export type GameEngine = "godot" | "unreal" | "unity"

export interface SambaShare {
  enabled: boolean
  share_name: string
  user: string
  platform: "linux" | "mac"
}

export interface EngineRun {
  schema_version: 1
  kind: "unreal-build" | "unreal-test"
  status: "passed" | "failed"
  exit_code: number
  finished_at: string
  log_path: string
}

export interface GameProject {
  project_id: string
  entry_kind: EntryKind
  engine: GameEngine
  engine_version: string
  engine_project_name: string
  engine_project_path: string
  engine_project_ready: boolean
  last_engine_run: EngineRun | null
  title: string
  idea: string
  genre: string
  target_platform: TargetPlatform
  core_action: string
  success_condition: string
  current_step: number
  revision: number
  created_at: string
  updated_at: string
  sharing: SambaShare
}

export interface SharingStatus {
  available: boolean
  running: boolean
  user: string
  platform: "linux" | "mac"
}

export interface GameStudioOverview {
  projects: GameProject[]
  sharing: SharingStatus
}

export interface ProjectCreate {
  entry_kind: EntryKind
  engine: GameEngine
  engine_version: string
  title: string
  idea: string
  genre: string
  target_platform: TargetPlatform
}

export type ProjectPatch = Partial<Pick<GameProject,
  "title" | "idea" | "genre" | "target_platform" | "core_action" | "success_condition" | "current_step"
>> & { revision: number }
