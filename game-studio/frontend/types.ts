export type EntryKind = "new" | "adopt" | "archive"
export type TargetPlatform = "desktop" | "web" | "mobile"

export interface GameDraft {
  draft_id: string
  entry_kind: EntryKind
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
}

export interface WorkstationStatus {
  code: "core_update_required" | "not_connected" | "offline" | "approval_required" | "ready_for_binding"
  ready: boolean
  build_available: false
}

export interface GameStudioOverview {
  drafts: GameDraft[]
  workstation: WorkstationStatus
  runner: {
    code: "runner_pending_pr4"
    build_available: false
  }
}

export interface DraftCreate {
  entry_kind: EntryKind
  title: string
  idea: string
  genre: string
  target_platform: TargetPlatform
}

export type DraftPatch = Partial<Pick<GameDraft,
  "title" | "idea" | "genre" | "target_platform" | "core_action" | "success_condition" | "current_step"
>> & { revision: number }
