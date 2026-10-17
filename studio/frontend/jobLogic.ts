import type { Job } from "./planApi"

/** Jüngster Auftrag für ein Ziel (Shot) oder null. */
export function jobFor(jobs: Job[], target: string): Job | null {
  return jobs.filter((j) => j.target === target).sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null
}

/** Anzahl laufender Aufträge (für die Anzeige oben). */
export function runningJobs(jobs: Job[]): number {
  return jobs.filter((j) => j.status === "running" || j.status === "queued").length
}

const KNOWN = new Set(["no_key", "provider_rejected", "provider_unreachable", "empty_answer", "bad_image", "interrupted", "shot_gone"])

/** Meldung zu einem fehlgeschlagenen Auftrag (Code → Text). Leer, wenn nichts schiefging. */
export function jobText(t: (k: string) => string, job: Job | null): string {
  if (!job || job.status !== "failed") return ""
  return t(`job_err.${job.error && KNOWN.has(job.error) ? job.error : "internal"}`)
}
