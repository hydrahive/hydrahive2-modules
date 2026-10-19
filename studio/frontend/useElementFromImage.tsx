import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { LibraryItem } from "./api"
import { ElementFromImageDialog } from "./ElementFromImageDialog"
import { describeApi } from "./elementPhotoLogic"
import { errorText } from "./planLogic"

/** Bibliothek → neue Figur/neuer Ort aus einem Bild (C2): anlegen, beschreiben lassen, in „Planen“ öffnen. */
export function useElementFromImage(projectId: string, open: (elementId: string) => void, notice: (text: string) => void) {
  const { t } = useTranslation("studio")
  const [target, setTarget] = useState<{ item: LibraryItem; kind: "character" | "place" } | null>(null)
  const [busy, setBusy] = useState(false)
  const confirm = async (name: string) => {
    if (!target) return
    setBusy(true)
    try {
      const el = await describeApi.fromImage(projectId, { rel: target.item.rel, kind: target.kind, name })
      setTarget(null)
      open(el.id)
      notice(t("media_as_done", { name }))
      try {                                                         // Bild bleibt Vorlage, auch ohne Text
        await describeApi.describe(projectId, el.id)
        open(el.id)
        notice(t("photo_described"))
      } catch (e) { notice(errorText(t, e)) }
    } catch (e) { notice(errorText(t, e)) } finally { setBusy(false) }
  }
  const dialog = target
    ? <ElementFromImageDialog kind={target.kind} suggestion={target.item.name} busy={busy} onConfirm={(n) => void confirm(n)} onClose={() => setTarget(null)} />
    : null
  return { ask: (item: LibraryItem, kind: "character" | "place") => setTarget({ item, kind }), dialog }
}
