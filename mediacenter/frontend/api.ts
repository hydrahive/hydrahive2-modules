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

const ERROR_LABELS: Record<string, string> = {
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

export function errorMessage(error: unknown): string {
  if (!(error instanceof Error)) return "Unbekannter Fehler"
  return ERROR_LABELS[error.message] ?? error.message
}
