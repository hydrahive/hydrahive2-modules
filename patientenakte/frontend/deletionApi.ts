import { api } from "@/shared/api-client"

// ── Daten löschen (nur eigene Daten, Bestätigungswort Pflicht) ──────────────
export type DeletionScope = "apple_health" | "fhir" | "ega" | "all"
export const DELETION_CONFIRM_WORD = "LÖSCHEN"

export interface DeletionOverview {
  apple_health: { raw: number; daily: number; first_day: string | null; last_day: string | null }
  fhir: number
  ega: number
  akte: boolean
}

export interface DeletionResult {
  scope: DeletionScope
  deleted: Record<string, number>
  raw_kept_partial?: number
}

export const deletionApi = {
  overview: () => api.get<DeletionOverview>("/modules/patientenakte/data-deletion/overview"),
  remove: (scope: DeletionScope, confirm: string, range?: { from: string; to: string }) =>
    api.post<DeletionResult>("/modules/patientenakte/data-deletion", { scope, confirm, ...(range ?? {}) }),
}
