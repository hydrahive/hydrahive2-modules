import { Loader2, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Backdrop } from "./StudioDialogs"

interface Props {
  count: number
  busy: boolean
  onConfirm: () => void
  onClose: () => void
}

/** Rückfrage, bevor „In Shots zerlegen“ Shots mit Bild/Video ersetzt (kein Browser-Popup). */
export function DecomposeDialog({ count, busy, onConfirm, onClose }: Props) {
  const { t } = useTranslation("studio")
  return (
    <Backdrop onClose={onClose} label={t("decompose")}>
      <div className="space-y-3 p-4 text-xs text-[#c3ccdd]">
        <p className="text-sm text-[#e8eef8]">{t("decompose_replace_question", { count })}</p>
        <p className="rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2.5 py-2 leading-relaxed text-[#9aa7bc]">{t("decompose_replace_hint")}</p>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#9aa7bc] hover:text-[#e8eef8]">{t("cancel")}</button>
          <button type="button" onClick={onConfirm} disabled={busy} data-decompose-confirm
            className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} {t("decompose_replace_run")}
          </button>
        </div>
      </div>
    </Backdrop>
  )
}
