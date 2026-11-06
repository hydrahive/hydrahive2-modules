import { api } from "@/shared/api-client"

export const BASE = "/modules/vibe"

export interface VibeProject {
  project_id: string; name: string; state: "new" | "setting_up" | "ready" | "sleeping" | "failed"
  model: string; progress: string; error_code: string; error_step: string; error_detail: string; heal_enabled: boolean
}
export interface VibeState { incus: boolean; error_code: string; projects: VibeProject[] }
export interface VibeModel { id: string; label: string; provider: string }
export interface VibeVersion { commit_id: string; summary: string; created_at: string }

export const getState = () => api.get<VibeState>(`${BASE}/state`)
export const getModels = () => api.get<{ default: string; default_listed: boolean; items: VibeModel[] }>(`${BASE}/models`)
export const createProject = (name: string, model: string) => api.post<{ project_id: string }>(`${BASE}/projects`, { name, model })
export const setModel = (id: string, model: string) => api.post<{ model: string }>(`${BASE}/projects/${id}/model`, { model })
export const removeProject = (id: string) => api.delete<{ removed: boolean }>(`${BASE}/projects/${id}`)
export const retryProject = (id: string) => api.post<{ started: boolean }>(`${BASE}/projects/${id}/retry`, {})
export const openChat = (id: string) => api.post<{ session_id: string; agent_id: string }>(`${BASE}/projects/${id}/chat`, {})
export const openPreview = (id: string) => api.post<{ url: string }>(`${BASE}/projects/${id}/preview/open`, {})
export const getVersions = (id: string) => api.get<{ versions: VibeVersion[] }>(`${BASE}/projects/${id}/versions`)
export const restoreVersion = (id: string, sha: string) => api.post<unknown>(`${BASE}/projects/${id}/versions/${sha}/restore`, {})

/** Fehlercode aus einer Antwort des Servers → Schlüssel für die Texte (unbekannt → allgemein). */
export function errorKey(e: unknown, known: readonly string[]): string {
  const code = typeof e === "object" && e !== null ? ((e as { code?: unknown; detail?: { code?: unknown } }).code
    ?? (e as { detail?: { code?: unknown } }).detail?.code) : undefined
  return typeof code === "string" && known.includes(code) ? `err.${code}` : "err.general"
}
