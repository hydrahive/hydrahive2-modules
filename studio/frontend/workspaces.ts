/** Arbeitsbereiche des Studios (Spec „Arbeitsbereiche“), Reihenfolge = Reiter oben. */
export const WORKSPACES = ["plan", "generate", "edit", "audio", "subtitles", "deliver"] as const
export type Workspace = (typeof WORKSPACES)[number]
