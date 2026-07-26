import i18n from "@/i18n"
import { api } from "@/shared/api-client"
import type {
  ConnectionTest, EnqueueResponse, Job, ModuleStatus, SearchFilters, SearchResponse,
} from "./types"

const BASE = "/modules/mediacenter"

export const mediacenterApi = {
  status: () => api.get<ModuleStatus>(`${BASE}/status`),
  testConnections: () => api.post<ConnectionTest>(`${BASE}/connections/test`, {}),
  search: (body: SearchFilters) => api.post<SearchResponse>(`${BASE}/search`, body),
  enqueue: (resultId: string) => api.post<EnqueueResponse>(`${BASE}/enqueue`, {
    result_id: resultId,
    priority: "default",
  }),
  queue: () => api.get<Job[]>(`${BASE}/queue`),
  history: () => api.get<Job[]>(`${BASE}/history`),
}

const DE_ERRORS: Record<string, string> = {
  indexer_credential_missing: "Treasure Maps ist noch nicht konfiguriert.",
  sab_credential_missing: "SABnzbd ist noch nicht konfiguriert.",
  indexer_auth_failed: "Treasure Maps hat den API-Schlüssel abgelehnt.",
  sab_auth_failed: "SABnzbd hat den API-Schlüssel abgelehnt.",
  indexer_unavailable: "Treasure Maps ist momentan nicht erreichbar.",
  sab_unavailable: "SABnzbd ist momentan nicht erreichbar.",
  indexer_capabilities_missing: "Treasure Maps bietet nicht alle benötigten Suchfunktionen.",
  sab_categories_missing: "In SABnzbd fehlen benötigte Zielkategorien.",
  result_unavailable: "Der Treffer ist abgelaufen oder nicht mehr verfügbar.",
  enqueue_status_uncertain: "Übergabestatus unklar. Bitte direkt in SABnzbd prüfen.",
  enqueue_manual_review_required: "Dieser Auftrag muss direkt in SABnzbd geprüft werden.",
  mediacenter_rate_limited: "Zu viele Anfragen. Bitte kurz warten.",
  mediacenter_request_invalid: "Die Eingaben sind ungültig.",
}
const EN_ERRORS: Record<string, string> = {
  indexer_credential_missing: "Treasure Maps is not configured yet.",
  sab_credential_missing: "SABnzbd is not configured yet.",
  indexer_auth_failed: "Treasure Maps rejected the API key.",
  sab_auth_failed: "SABnzbd rejected the API key.",
  indexer_unavailable: "Treasure Maps is currently unavailable.",
  sab_unavailable: "SABnzbd is currently unavailable.",
  indexer_capabilities_missing: "Treasure Maps lacks required search capabilities.",
  sab_categories_missing: "Required SABnzbd categories are missing.",
  result_unavailable: "The result expired or is no longer available.",
  enqueue_status_uncertain: "Submission status is uncertain. Check SABnzbd directly.",
  enqueue_manual_review_required: "This job must be reviewed directly in SABnzbd.",
  mediacenter_rate_limited: "Too many requests. Please wait briefly.",
  mediacenter_request_invalid: "The input is invalid.",
}

export function errorMessage(error: unknown): string {
  const fallback = i18n.language.startsWith("en") ? "Unknown error" : "Unbekannter Fehler"
  if (!(error instanceof Error)) return fallback
  const labels = i18n.language.startsWith("en") ? EN_ERRORS : DE_ERRORS
  return labels[error.message] ?? error.message
}
