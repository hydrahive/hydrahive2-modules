export type EntryKind = "new" | "adopt" | "archive"
export type TargetPlatform = "desktop" | "web" | "mobile"
export type GameEngine = "godot" | "unreal" | "unity"

export interface SambaShare {
  enabled: boolean
  share_name: string
  user: string
  platform: "linux" | "mac"
}

export interface GameProject {
  project_id: string
  entry_kind: EntryKind
  engine: GameEngine
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

export interface WorkstationStatus {
  code: "core_update_required" | "not_connected" | "offline" | "approval_required" | "ready_for_binding"
  ready: boolean
  build_available: false
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
  workstation: WorkstationStatus
  runner: { code: "runner_pending_pr4"; build_available: false }
}

export interface ProjectCreate {
  entry_kind: EntryKind
  engine: GameEngine
  title: string
  idea: string
  genre: string
  target_platform: TargetPlatform
}

export type ProjectPatch = Partial<Pick<GameProject,
  "title" | "idea" | "genre" | "target_platform" | "core_action" | "success_condition" | "current_step"
>> & { revision: number }
