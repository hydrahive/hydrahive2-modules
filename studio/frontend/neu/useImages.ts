/** G3: Aktionen im Schritt „Bilder“ – einzeln/alle erzeugen, blättern, wegwerfen, „Mit dabei“. */
import { useState } from "react"
import { mediaApi } from "../mediaLogic"
import { planApi } from "../planApi"
import { useJobs } from "../useJobs"
import { castToggle, variantStep, type ImageCardData } from "./guidedLogic"
import type { GuidedState } from "./useGuided"

export function useImages(g: GuidedState, active: boolean) {
  const js = useJobs(g.pid, active, () => { void g.reload() })
  const [dropping, setDropping] = useState<ImageCardData | null>(null)
  const batch = js.jobs.find((j) => j.kind === "images_all" && (j.status === "running" || j.status === "queued")) ?? null

  const after = async (fn: () => Promise<unknown>) => { await g.run(fn); await js.reload() }
  const make = (c: ImageCardData) => after(() => planApi.generateImage(g.pid, c.sceneId, c.shot.id))
  const all = () => after(() => planApi.batchStart(g.pid, "images_all"))
  const stop = () => batch ? after(() => planApi.cancelJob(g.pid, batch.id)) : Promise.resolve()
  const flip = (c: ImageCardData, dir: -1 | 1) => {
    const rel = variantStep(c.shot, dir)
    if (rel) void g.run(() => planApi.chooseVariant(g.pid, c.sceneId, c.shot.id, rel))
  }
  const cast = (c: ImageCardData, id: string) => void g.run(() => planApi.saveShot(g.pid, c.sceneId, c.shot.id, castToggle(c.shot, id)))
  const confirmDrop = () => {
    const d = dropping
    if (!d?.shot.image_rel) return
    const rel = d.shot.image_rel
    void g.run(() => mediaApi.remove(g.pid, rel))
      .then(() => setDropping(null))
  }
  return { jobs: js.jobs, batch, dropping, setDropping, make, all, stop, flip, cast, confirmDrop }
}

export type ImageActions = ReturnType<typeof useImages>
