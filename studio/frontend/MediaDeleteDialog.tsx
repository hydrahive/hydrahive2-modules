import { Loader2, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { usageLines, type MediaUsage } from "./mediaLogic"
import { Backdrop } from "./StudioDialogs"

interface Props {
  name: string
  /** null = wird noch geprüft */
  usage: MediaUsage | null
  busy: boolean
  onConfirm: () => void
  onClose: () => void
}

/** Rückfrage vor dem Löschen einer Datei (C1): nennt, wo sie benutzt wird und was danach passiert. */
export function MediaDeleteDialog({ name, usage, busy, onConfirm, onClose }: Props) {
  const { t } = useTranslation("studio")
  const lines = usage ? usageLines(usage) : []
  return (
    <Backdrop onClose={onClose} label={t("media_delete")}>
      <div className="space-y-3 p-4 text-xs text-[#c3ccdd]" data-media-delete-dialog>
        <p className="text-sm text-[#e8eef8]">{t("media_delete_question", { name })}</p>
        {!usage ? <p className="flex items-center gap-1.5 text-[#68758a]"><Loader2 size={12} className="animate-spin" /> {t("media_usage_loading")}</p>
          : lines.length ? (
            <>
              <ul className="list-disc space-y-1 pl-4 text-[#ffb86b]">{lines.map((l) => <li key={l.key}>{t(l.key, l.o)}</li>)}</ul>
              <p className="leading-relaxed text-[#8d9ab0]">{t("media_delete_after")}</p>
            </>
          ) : <p className="text-[#8d9ab0]">{t("media_unused")}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#8d9ab0] hover:text-[#e8eef8]">{t("cancel")}</button>
          <button type="button" onClick={onConfirm} disabled={busy || !usage} data-media-delete-confirm
            className="flex items-center gap-1.5 rounded-[4px] bg-[#ff6b8a] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />} {t("delete")}
          </button>
        </div>
      </div>
    </Backdrop>
  )
}
