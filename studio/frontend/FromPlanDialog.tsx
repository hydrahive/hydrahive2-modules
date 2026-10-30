import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Backdrop } from "./StudioDialogs"

/** Rückfrage, bevor die Zeitleiste aus dem Drehbuch neu aufgebaut wird (kein Browser-Popup). */
export function FromPlanDialog({ count, busy, onConfirm, onClose }: { count: number; busy: boolean; onConfirm: () => void; onClose: () => void }) {
  const { t } = useTranslation("studio")
  return (
    <Backdrop onClose={onClose} label={t("cut_from_plan")}>
      <div className="space-y-3 p-4 text-xs text-[#c3ccdd]" data-cut-replace-dialog>
        <h3 className="text-sm font-black text-[#e8eef8]">{t("cut_from_plan")}</h3>
        <p className="text-sm text-[#e8eef8]">{t("cut_replace_question", { count })}</p>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#9aa7bc] hover:text-[#e8eef8]">{t("cancel")}</button>
          <button type="button" onClick={onConfirm} disabled={busy} data-cut-replace
            className="flex items-center gap-1.5 rounded-[4px] bg-[#ff6b8a] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
            {busy && <Loader2 size={13} className="animate-spin" />} {t("cut_replace")}
          </button>
        </div>
      </div>
    </Backdrop>
  )
}
