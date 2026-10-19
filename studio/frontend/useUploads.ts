import { useCallback, useState } from "react"
import { useTranslation } from "react-i18next"
import { describeApi, needsDescription } from "./elementPhotoLogic"
import { planApi, type PlanElement } from "./planApi"
import { errorText } from "./planLogic"
import { uploadApi, uploadSummary } from "./uploadLogic"
import type { PlanState } from "./usePlan"

/** Hochladen (7a): in die Bibliothek bzw. als Referenzbild an einen Baustein. Danach Bibliothek und Drehbuch neu laden. */
export function useUploads(projectId: string, p: PlanState, reloadLibrary: () => void, notice: (text: string) => void) {
  const { t } = useTranslation("studio")
  const [busy, setBusy] = useState(false)
  const [describing, setDescribing] = useState<string | null>(null)

  /** C2: Beschreibung + Aussehen aus dem Foto. Ungespeicherte Felder zuerst speichern. */
  const describe = useCallback(async (elementId: string, pending: Partial<PlanElement> | null) => {
    setDescribing(elementId)
    try {
      await p.act(async () => {
        if (pending) await planApi.saveElement(projectId, elementId, pending)
        await describeApi.describe(projectId, elementId)
      }, t("photo_described"))
    } finally { setDescribing(null) }
  }, [projectId, p, t])

  const library = useCallback(async (files: File[]) => {
    if (!projectId || !files.length) return
    setBusy(true)
    try {
      const r = await uploadApi.library(projectId, files)
      const sum = uploadSummary(r.files)
      const failed = sum.failed.map((f) => `${f.name}: ${t(`err.${f.error}`)}`).join(" · ")
      notice([t(sum.key, { count: sum.count }), failed].filter(Boolean).join(" "))
      reloadLibrary()
    } catch (e) { notice(errorText(t, e)) }
    finally { setBusy(false) }
  }, [projectId, reloadLibrary, notice, t])

  /** Noch nicht gespeicherte Felder zuerst speichern – sonst gingen sie beim Neuladen verloren. */
  const reference = useCallback(async (elementId: string, file: File, pending: Partial<PlanElement> | null) => {
    setBusy(true)
    try {
      let saved: PlanElement | null = null
      const ok = await p.act(async () => {
        if (pending) await planApi.saveElement(projectId, elementId, pending)
        saved = await uploadApi.reference(projectId, elementId, file)
      }, t("upload_reference_done"))
      reloadLibrary()
      if (ok && saved && needsDescription(saved)) void describe(elementId, null)   // erstes Foto: gleich beschreiben (C2)
    } finally { setBusy(false) }
  }, [projectId, p, reloadLibrary, t, describe])

  return { busy, describing, library: (f: File[]) => void library(f),
    reference: (id: string, f: File, pending: Partial<PlanElement> | null) => void reference(id, f, pending),
    describe: (id: string, pending: Partial<PlanElement> | null) => void describe(id, pending) }
}
