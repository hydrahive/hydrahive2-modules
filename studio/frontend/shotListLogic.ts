/** Reiter „Erzeugen“: Stand je Shot und Zähler (rein, damit testbar). */
import { latestJob } from "./jobLogic"
import type { Job, Plan, Shot } from "./planApi"

export type ShotState = "none" | "image" | "video" | "running" | "failed"

/** Ein laufender oder zuletzt fehlgeschlagener Auftrag hat Vorrang, sonst zählt, was am Shot hängt. */
export function shotState(shot: Shot, jobs: Job[]): ShotState {
  const last = latestJob(jobs, shot.id)
  if (last?.status === "running" || last?.status === "queued") return "running"
  if (last?.status === "failed") return "failed"
  return shot.video_rel ? "video" : shot.image_rel ? "image" : "none"
}

export function shotCounts(plan: Plan | null): { total: number; image: number; video: number } {
  const shots = plan?.scenes.flatMap((s) => s.shots) ?? []
  return { total: shots.length, image: shots.filter((s) => s.image_rel).length, video: shots.filter((s) => s.video_rel).length }
}
