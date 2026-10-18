import { api } from "@/shared/api-client"
import type { Job } from "./planApi"

/** Heraushören (Spec „Bauplan 6b“): Werte für den Dialog, Auftrag starten, fertigen Auftrag erkennen. Rein, damit testbar. */
export interface HearInfo { seconds: number; model: string; cloud: boolean; existing: number; max_seconds: number }

const base = (pid: string, lang: string) => `/modules/studio/projects/${encodeURIComponent(pid)}/subtitles/${encodeURIComponent(lang)}/from-audio`
export const hearApi = {
  info: (pid: string, lang: string) => api.get<HearInfo>(base(pid, lang)),
  start: (pid: string, lang: string, replace: boolean) => api.post<Job>(base(pid, lang), replace ? { replace: true } : {}),
}

/** Kosten laut Probe (18.10.): whisper-large-v3 ≈ 0,045 ct je Minute. Aufgerundet auf ganze Cent. */
const CENTS_PER_MINUTE = 0.045
export function costText(seconds: number): { key: "hear_cost_below" } | { key: "hear_cost_about"; cents: number } {
  const cents = (seconds / 60) * CENTS_PER_MINUTE
  return cents < 1 ? { key: "hear_cost_below" } : { key: "hear_cost_about", cents: Math.ceil(cents) }
}

/** In diesem Fenster gestarteter Auftrag, der fertig (oder fehlgeschlagen/abgebrochen) ist – sonst null. */
export function finishedHear(jobs: Job[], pending: Set<string>): Job | null {
  return jobs.find((j) => j.kind === "transcribe" && pending.has(j.id) && (j.status === "done" || j.status === "failed" || j.status === "cancelled")) ?? null
}

/** Länge für den Dialog (m:ss). */
export function lengthText(seconds: number): string {
  const s = Math.round(seconds)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`
}
