import { api } from "@/shared/api-client"
import type { LawItem } from "./legalFormat"

const BASE = "/modules/legal"

export interface SearchHit {
  abbr: string
  enbez: string
  title: string
  heading: string
  snippet: string
  match: "exact" | "text"
  law_key: string
}

export interface NormDetail {
  citation: string
  abbr: string
  enbez: string
  title: string
  gliederung: string
  text: string
  law_title: string
  stand: string
  fetched_at: string
  valid_to: string | null
  url: string
}

export interface SyncState {
  last: { state: string; total: number; changed: number; errors: { key: string; error: string }[]; finished_at: string | null } | null
  running: boolean
}

export const legalApi = {
  laws: () => api.get<{ laws: LawItem[]; core_total: number; groups: string[] }>(`${BASE}/laws`),
  law: (key: string) =>
    api.get<LawItem & { norms: { enbez: string; title: string; gliederung: string }[] }>(`${BASE}/laws/${encodeURIComponent(key)}`),
  search: (q: string, law?: string) =>
    api.get<{ hits: SearchHit[] }>(`${BASE}/search?${new URLSearchParams({ q, limit: "20", ...(law ? { law } : {}) })}`),
  norm: (citation: string) => api.get<NormDetail>(`${BASE}/norm?${new URLSearchParams({ citation })}`),
  syncState: () => api.get<SyncState>(`${BASE}/sync`),
  syncNow: () => api.post<{ started: boolean }>(`${BASE}/sync`, {}),
}
