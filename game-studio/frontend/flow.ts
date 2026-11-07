import type { GameProject } from "./types"

export const FLOW_STEPS = ["idea", "brief", "slice", "ready"] as const
export type FlowStep = typeof FLOW_STEPS[number]

export function completedStep(project: GameProject, step: number): boolean {
  if (step === 1) return Boolean(project.title.trim() && project.idea.trim())
  if (step === 2) return Boolean(project.genre.trim() && project.target_platform)
  if (step === 3) return Boolean(project.core_action.trim() && project.success_condition.trim())
  return false
}

export function highestAvailableStep(project: GameProject): number {
  if (!completedStep(project, 1)) return 1
  if (!completedStep(project, 2)) return 2
  if (!completedStep(project, 3)) return 3
  return 4
}
