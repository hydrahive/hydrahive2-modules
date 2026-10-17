import { Loader2, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Backdrop } from "./StudioDialogs"

interface Props {
  name: string
  busy: boolean
  onConfirm: () => void
  onClose: () => void
}

/** Löschen über einen eigenen Dialog (kein Rückfrage-Popup des Browsers). */
export function DeleteDialog({ name, busy, onConfirm, onClose }: Props) {
  const { t } = useTranslation("studio")
  return (
    <Backdrop onClose={onClose} label={t("delete")}>
      <div className="space-y-3 p-4 text-xs text-[#c3ccdd]">
        <p className="text-sm text-[#e8eef8]">{t("delete_question", { name })}</p>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#8d9ab0] hover:text-[#e8eef8]">{t("cancel")}</button>
          <button type="button" onClick={onConfirm} disabled={busy} data-delete-confirm
            className="flex items-center gap-1.5 rounded-[4px] bg-[#ff6b8a] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />} {t("delete")}
          </button>
        </div>
      </div>
    </Backdrop>
  )
}
