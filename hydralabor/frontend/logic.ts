/** Hydra-Labor: reine Hilfen. Platzhalter – Umsetzung im nächsten Commit. */
export interface LastTest { ok?: boolean; passed?: number; failed?: number; summary?: string; failures?: string[]; at?: string }
export interface LabState {
  step: "start" | "ready"; running: string; progress: string; error_code: string; error_step: string; model: string
  cpu: number; ram_mb: number; disk_gb: number; last_net_ok: string; last_test: LastTest; project_id: string
  agent_id: string; container_running: boolean
}
export interface Check { id: string; ok: boolean; code: string; have: number | string | null; need: number | string | null }
export interface Checks { ok: boolean; checks: Check[] }
export interface Limits { cpu: number; ram_mb: number; disk_gb: number }
export interface Model { id: string; label: string; provider: string }
export const CREATE_STEPS: string[] = []
export const errorKey = (_e: unknown): string => ""
export const progressOf = (_s: LabState) => ({ index: -2, pct: -1 })
export const limitsError = (_l: Limits): string => "x"
export const testLine = (_t: LastTest): { key: string; passed: number; failed: number } | null => ({ key: "", passed: -1, failed: -1 })
