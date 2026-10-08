// T1e – Team-Knöpfe (Plan schreib-team-t1e.md): Helfer ohne Chat beauftragen. Reine Hilfen + Aufrufe.
import { call } from "./api"

export type JobScope = "scene" | "chapter"
export type JobStatus = "queued" | "running" | "done" | "error" | "cancelled"

export interface CatalogEntry { key: string; label: string; scope: JobScope; role: string; available: boolean }

export interface TeamJob {
  id: string; job: string; role: string; agent_name: string; place_id: string; place_title: string
  status: JobStatus; summary: string; error: string; cost_micros: number | null; estimate_micros: number | null
  session_id: string; at: string; finished_at: string
}

export interface JobEstimate {
  job: string; place_id: string; place_title: string; model: string
  input_tokens: number; output_tokens: number; cost_micros: number | null
}

/** Stelle eines Knopfs: die Szene selbst oder ihr Kapitel. */
export function placeFor(scope: JobScope, sceneId: string, chapters: Record<string, string[]>): string | null {
  if (scope === "scene") return sceneId
  return Object.keys(chapters).find((c) => chapters[c].includes(sceneId)) ?? null
}

export const isActive = (j: TeamJob) => j.status === "queued" || j.status === "running"

/** Läuft für diesen Knopf an dieser Stelle schon etwas? */
export function activeFor(jobs: TeamJob[], key: string, placeId: string): TeamJob | undefined {
  return jobs.find((j) => isActive(j) && j.job === key && j.place_id === placeId)
}

/** Nachfragen nur, solange ein Auftrag läuft (sonst keine Last). */
export const needsPolling = (jobs: TeamJob[] | null) => !!jobs && jobs.some(isActive)

export const JOB_POLL_MS = 5_000

const jobsPath = (pid: string, bid: string) => `/projects/${encodeURIComponent(pid)}/books/${encodeURIComponent(bid)}/team/jobs`

export const jobsApi = {
  catalog: (pid: string, bid: string) => call<CatalogEntry[]>("GET", `${jobsPath(pid, bid)}/catalog`),
  list: (pid: string, bid: string) => call<TeamJob[]>("GET", jobsPath(pid, bid)),
  estimate: (pid: string, bid: string, job: string, placeId: string) =>
    call<JobEstimate>("POST", `${jobsPath(pid, bid)}/estimate`, { job, place_id: placeId }),
  start: (pid: string, bid: string, job: string, placeId: string) =>
    call<TeamJob>("POST", jobsPath(pid, bid), { job, place_id: placeId }),
  cancel: (pid: string, bid: string, id: string) =>
    call<TeamJob>("POST", `${jobsPath(pid, bid)}/${encodeURIComponent(id)}/cancel`),
}
