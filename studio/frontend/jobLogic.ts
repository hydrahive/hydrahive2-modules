import type { Job } from "./planApi"

/** Jüngster Auftrag für ein Ziel (Shot) oder null – optional nur einer Art (Bild/Video). */
export function latestJob(jobs: Job[], target: string, kind?: Job["kind"]): Job | null {
  return jobs.filter((j) => j.target === target && (!kind || j.kind === kind))
    .sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null
}

/** Jüngster Auftrag für ein Ziel (Shot), gleich welcher Art. */
export function jobFor(jobs: Job[], target: string): Job | null {
  return latestJob(jobs, target)
}

/** Anzahl laufender Aufträge (für die Anzeige oben). */
export function runningJobs(jobs: Job[]): number {
  return jobs.filter((j) => j.status === "running" || j.status === "queued").length
}

const KNOWN = new Set(["no_key", "provider_rejected", "provider_unreachable", "empty_answer", "bad_image", "interrupted", "shot_gone",
  "video_failed", "timeout", "bad_url", "too_big", "bad_video", "image_gone", "render_failed", "bad_audio", "no_text"])

/** Meldung zu einem fehlgeschlagenen Auftrag (Code → Text). Leer, wenn nichts schiefging. */
export function jobText(t: (k: string) => string, job: Job | null): string {
  if (!job || job.status !== "failed") return ""
  const sound = job.kind === "speech" || job.kind === "speech_all"
  if (job.error === "no_key" && sound) return t("job_err.no_key_voice")             // „Für Bilder …“ passt hier nicht
  return t(`job_err.${job.error && KNOWN.has(job.error) ? job.error : "internal"}`)
}

/** Sammelauftrag (mehrere Shots/Szenen) statt Einzelauftrag? */
export function isBatch(job: Job): boolean {
  return job.kind === "decompose_all" || job.kind === "images_all" || job.kind === "videos_all" || job.kind === "speech_all"
}

/** Der laufende Sammelauftrag des Projekts oder null. */
export function activeBatch(jobs: Job[]): Job | null {
  return jobs.find((j) => isBatch(j) && (j.status === "running" || j.status === "queued")) ?? null
}
