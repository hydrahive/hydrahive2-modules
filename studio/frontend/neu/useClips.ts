/** G4: Aktionen im Schritt „Bewegung“ – einzeln/alle bewegen, Standbild, Bewegung wegwerfen. */
import { useState } from "react"
import { mediaApi } from "../mediaLogic"
import { planApi } from "../planApi"
import { useJobs } from "../useJobs"
import type { ImageCardData } from "./guidedLogic"
import type { GuidedState } from "./useGuided"

export function useClips(g: GuidedState, active: boolean) {
  const js = useJobs(g.pid, active, () => { void g.reload() })
  const [dropping, setDropping] = useState<ImageCardData | null>(null)
  const batch = js.jobs.find((j) => j.kind === "videos_all" && (j.status === "running" || j.status === "queued")) ?? null

  const after = async (fn: () => Promise<unknown>) => { await g.run(fn); await js.reload() }
  const move = (c: ImageCardData) => after(() => planApi.generateVideo(g.pid, c.sceneId, c.shot.id))
  const all = () => after(() => planApi.batchStart(g.pid, "videos_all"))
  const stop = () => batch ? after(() => planApi.cancelJob(g.pid, batch.id)) : Promise.resolve()
  const still = (c: ImageCardData, v: boolean) => void g.run(() => planApi.saveShot(g.pid, c.sceneId, c.shot.id, { still: v }))
  const confirmDrop = () => {
    const rel = dropping?.shot.video_rel
    if (!rel) return
    void g.run(() => mediaApi.remove(g.pid, rel)).then(() => setDropping(null))
  }
  return { jobs: js.jobs, batch, dropping, setDropping, move, all, stop, still, confirmDrop }
}

export type ClipActions = ReturnType<typeof useClips>
