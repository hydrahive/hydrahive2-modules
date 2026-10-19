/** G2: Aktionen für Figuren & Orte – speichern, Foto hochladen (+ beschreiben + Probebild), Probebild, löschen. */
import { useState } from "react"
import { describeApi } from "../elementPhotoLogic"
import { useJobs } from "../useJobs"
import { planApi, type PlanElement } from "../planApi"
import { errorText } from "../planLogic"
import { uploadApi } from "../uploadLogic"
import { castOpen } from "./guidedLogic"
import type { GuidedState } from "./useGuided"

type T = (k: string, o?: Record<string, unknown>) => string

export function useCast(g: GuidedState, t: T, active: boolean) {
  const jobsState = useJobs(g.pid, active, () => { void g.reload() })
  const [uploading, setUploading] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<PlanElement | null>(null)

  const fields = (e: PlanElement) => ({ kind: e.kind, name: e.name, description: e.description, style_anchor: e.style_anchor,
    palette: e.palette, references: e.references, probe_rel: e.probe_rel ?? "", approved: !!e.approved, no_photo: !!e.no_photo })

  const save = (e: PlanElement, patch: Partial<PlanElement>) => void g.run(() => planApi.saveElement(g.pid, e.id, { ...fields(e), ...patch }))

  const probe = async (id: string) => {
    await g.run(async () => { await planApi.probe(g.pid, id) })
    await jobsState.reload()
  }

  /** Foto geben: hochladen → „Kein Foto“ aus → ohne Beschreibung: aus dem Foto beschreiben → Probebild */
  const photo = async (e: PlanElement, file: File) => {
    setUploading(e.id)
    let ok = false
    await g.run(async () => {
      if (e.no_photo || e.probe_rel) await planApi.saveElement(g.pid, e.id, { ...fields(e), no_photo: false })
      await uploadApi.reference(g.pid, e.id, file)
      if (!e.description.trim()) await describeApi.describe(g.pid, e.id).catch(() => null)   // klappt das nicht: Foto reicht
      ok = true
    })
    setUploading(null)
    if (ok) await probe(e.id)
  }

  const add = (kind: "character" | "place") => void g.run(() =>
    planApi.addElement(g.pid, { kind, name: t(kind === "place" ? "guided.new_place" : "guided.new_character"), description: "", references: [] }))

  const confirmDelete = () => {
    const d = deleting
    if (!d) return
    void g.run(() => planApi.deleteElement(g.pid, d.id)).then(() => setDeleting(null))
  }

  return {
    jobs: jobsState.jobs, uploading, deleting, setDeleting, open: castOpen(g.plan?.elements ?? []),
    save, probe, photo, add, confirmDelete, errorOf: (e: unknown) => errorText(t, e),
  }
}

export type CastActions = ReturnType<typeof useCast>
