import { useState } from "react"
import { useTranslation } from "react-i18next"
import { MediaDeleteDialog } from "./MediaDeleteDialog"
import { mediaApi, type MediaUsage } from "./mediaLogic"
import { errorText } from "./planLogic"

/** Löschen einer Datei (C1) für alle Stellen gleich: Rückfrage mit Verwendung, löschen, danach alles neu laden. */
export function useMediaDelete(projectId: string, onDone: (rel: string) => void, notice: (text: string) => void) {
  const { t } = useTranslation("studio")
  const [target, setTarget] = useState<{ rel: string; name: string } | null>(null)
  const [usage, setUsage] = useState<MediaUsage | null>(null)
  const [busy, setBusy] = useState(false)

  const ask = (rel: string, name: string) => {
    setTarget({ rel, name }); setUsage(null)
    mediaApi.usage(projectId, rel).then(setUsage, (e) => { setTarget(null); notice(errorText(t, e)) })
  }
  const confirm = async () => {
    if (!target) return
    setBusy(true)
    try {
      await mediaApi.remove(projectId, target.rel)
      onDone(target.rel)
      notice(t("media_deleted"))
      setTarget(null)
    } catch (e) { notice(errorText(t, e)) } finally { setBusy(false) }
  }
  const dialog = target
    ? <MediaDeleteDialog name={target.name} usage={usage} busy={busy} onConfirm={() => void confirm()} onClose={() => setTarget(null)} />
    : null
  return { ask, askItem: (i: { rel: string; name: string }) => ask(i.rel, i.name), dialog }
}
