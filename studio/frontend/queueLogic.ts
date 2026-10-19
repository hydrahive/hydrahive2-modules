/** Warteschlange der Ausgabe (7c): reine Hilfen. Grenze wie auf dem Server (backend/render_queue.py MAX_PER_PROJECT). */
import type { Job } from "./planApi"

export const QUEUE_MAX = 5
const SHOWN = 6
type T = (k: string, o?: Record<string, unknown>) => string

const open = (j: Job) => j.status === "queued" || j.status === "running"

/** Film-Aufträge für die Liste: die neuesten SHOWN, älteste oben (Reihenfolge der Klicks). */
export function queueJobs(jobs: Job[]): Job[] {
  return jobs.filter((j) => j.kind === "render").sort((a, b) => a.created_at.localeCompare(b.created_at)).slice(-SHOWN)
}

/** Schon QUEUE_MAX Filme wartend oder laufend? */
export function queueFull(jobs: Job[]): boolean {
  return jobs.filter((j) => j.kind === "render" && open(j)).length >= QUEUE_MAX
}

/** Kann dieser Auftrag abgebrochen werden? */
export const cancellable = open

/** Meldung nach dem Klick: läuft gleich oder wartet auf Platz N. */
export function startedNotice(t: T, r: { status?: string; position?: number }): string {
  return r.status === "queued" && (r.position ?? 1) > 1 ? t("notice_render_queued", { position: r.position }) : t("notice_render_started")
}
