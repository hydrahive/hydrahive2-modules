import { api } from "@/shared/api-client"

const BASE = "/modules/homeassistant"

export interface HAState {
  entity_id: string
  state: string
  name: string
  domain: string
  unit?: string | null
  device_class?: string | null
  icon?: string | null
  last_changed?: string | null
  attributes: Record<string, unknown>
}

export interface HATestResult {
  ok: boolean
  message?: string
  config?: {
    location_name?: string
    version?: string
    time_zone?: string
    state?: string
  }
}

export interface HAFavorite {
  id: number
  entity_id: string
}

export const haApi = {
  test: (): Promise<HATestResult> => api.get<HATestResult>(`${BASE}/test`),

  states: (): Promise<HAState[]> => api.get<HAState[]>(`${BASE}/states`),

  state: (entityId: string): Promise<HAState> =>
    api.get<HAState>(`${BASE}/states/${entityId}`),

  callService: (
    domain: string,
    service: string,
    entity_id = "",
    data: Record<string, unknown> = {},
  ): Promise<{ changed: HAState[] }> =>
    api.post<{ changed: HAState[] }>(`${BASE}/service`, { domain, service, entity_id, data }),

  favorites: (): Promise<HAFavorite[]> => api.get<HAFavorite[]>(`${BASE}/favorites`),

  addFavorite: (entity_id: string): Promise<HAFavorite> =>
    api.post<HAFavorite>(`${BASE}/favorites`, { entity_id }),

  removeFavorite: (entity_id: string): Promise<{ removed: boolean }> =>
    api.delete<{ removed: boolean }>(`${BASE}/favorites/${entity_id}`),
}
