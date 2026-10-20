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

// ── Fälle (L2) ───────────────────────────────────────────────────────────────

export interface CaseRow {
  project_id: string
  title: string
  area: string
  status: "open" | "waiting" | "done"
  state: string
  summary: string
  facts: string
  goal: string
  our_ref: string
  their_ref: string
  created_by: string
  created_at: string
  updated_at: string
}
export interface CaseListItem extends CaseRow { role: string; next_deadline: { label: string; due_date: string } | null }
export interface Party { id: number; role: string; name: string; address: string; contact: string; note: string; created_at: string }
export interface Deadline {
  id: number
  label: string
  event_date: string
  kind: string
  amount: number
  start_rule: string
  due_date: string
  calc: { steps: string[]; warnings: string[]; state: string }
  status: "open" | "done" | "missed"
  note: string
  created_at: string
}
export interface CaseNote { id: number; author: "agent" | "user"; author_name: string; title: string; body: string; citations: { citation: string; found: boolean }[]; created_at: string }
export interface Proposal { id: number; kind: "party" | "deadline" | "fact"; payload: Record<string, unknown>; author_name: string; status: string; created_at: string }
export interface CaseSnapshot { case: CaseRow; state_name: string; parties: Party[]; deadlines: Deadline[]; notes: CaseNote[]; open_proposals: number; role: string }
export interface CalcResult { event_date: string; kind: string; amount: number; state: string; start: string; raw_end: string; due_date: string; weekday: string; steps: string[]; warnings: string[] }
export interface DeadlineInput { event_date: string; kind: string; amount: number; start_rule: string }

const c = (pid: string) => `${BASE}/cases/${encodeURIComponent(pid)}`

export const caseApi = {
  states: () => api.get<{ states: Record<string, string> }>(`${BASE}/states`),
  list: () => api.get<{ cases: CaseListItem[] }>(`${BASE}/cases`),
  create: (body: Partial<CaseRow> & { title: string; state: string; model?: string }) =>
    api.post<{ project_id: string; agent_id: string; case: CaseRow }>(`${BASE}/cases`, body),
  get: (pid: string) => api.get<CaseSnapshot>(c(pid)),
  patch: (pid: string, body: Partial<CaseRow>) => api.patch<CaseRow>(c(pid), body),
  addParty: (pid: string, body: Omit<Party, "id" | "created_at">) => api.post<Party>(`${c(pid)}/parties`, body),
  deleteParty: (pid: string, id: number) => api.delete<void>(`${c(pid)}/parties/${id}`),
  addDeadline: (pid: string, body: DeadlineInput & { label: string; note?: string }) => api.post<Deadline>(`${c(pid)}/deadlines`, body),
  setDeadlineStatus: (pid: string, id: number, status: Deadline["status"]) => api.patch<unknown>(`${c(pid)}/deadlines/${id}`, { status }),
  deleteDeadline: (pid: string, id: number) => api.delete<void>(`${c(pid)}/deadlines/${id}`),
  addNote: (pid: string, body: { title: string; body: string; citations?: string[] }) => api.post<CaseNote>(`${c(pid)}/notes`, body),
  deleteNote: (pid: string, id: number) => api.delete<void>(`${c(pid)}/notes/${id}`),
  proposals: (pid: string) => api.get<{ proposals: Proposal[] }>(`${c(pid)}/proposals`),
  decide: (pid: string, id: number, accept: boolean) => api.post<Proposal>(`${c(pid)}/proposals/${id}/${accept ? "accept" : "reject"}`, {}),
  chat: (pid: string) => api.post<{ session_id: string; url: string; agent_id: string }>(`${c(pid)}/chat`, {}),
  calc: (body: DeadlineInput & { state: string }) => api.post<CalcResult>(`${BASE}/deadline/calc`, body),
}
