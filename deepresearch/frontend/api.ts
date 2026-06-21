import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"

const BASE = "/modules/deepresearch"

export interface RunListItem {
  id: string
  question: string
  status: string
  created_at: string
}

export interface Source {
  url: string
  title: string
  image: string
}

export interface RunProgress {
  phase?: string
  round?: number
  queries?: number
  total_sources?: number
  total_findings?: number
  current?: { title: string; url: string } | null
  elapsed_s?: number
}

export interface RunResult {
  markdown: string
  sources: Source[]
  stats: Record<string, unknown>
  category: string
}

export interface Run {
  id: string
  question: string
  status: string // running | done | error
  category: string
  progress: RunProgress
  result: RunResult | null
  error: string | null
  created_at: string
}

export interface RunOptions {
  model?: string
  max_rounds?: number
  category?: string
}

export const startRun = (question: string, opts: RunOptions = {}) =>
  api.post<{ run_id: string }>(`${BASE}/runs`, { question, ...opts })

export const listRuns = () => api.get<RunListItem[]>(`${BASE}/runs`)

export const getRun = (id: string) => api.get<Run>(`${BASE}/runs/${id}`)

/** Report ist text/html → Raw-Fetch mit Bearer (der api-Client kann nur JSON). */
export async function fetchReportHtml(id: string): Promise<string> {
  const token = useAuthStore.getState().token
  const res = await fetch(`/api${BASE}/runs/${id}/report`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.text()
}
