import type { GameDraft } from "./types"

export const FLOW_STEPS = ["idea", "brief", "slice", "run", "evidence"] as const
export type FlowStep = typeof FLOW_STEPS[number]

export function completedStep(draft: GameDraft, step: number): boolean {
  if (step === 1) return Boolean(draft.title.trim() && draft.idea.trim())
  if (step === 2) return Boolean(draft.genre.trim() && draft.target_platform)
  if (step === 3) return Boolean(draft.core_action.trim() && draft.success_condition.trim())
  return false
}

export function highestAvailableStep(draft: GameDraft): number {
  if (!completedStep(draft, 1)) return 1
  if (!completedStep(draft, 2)) return 2
  if (!completedStep(draft, 3)) return 3
  return 4
}
