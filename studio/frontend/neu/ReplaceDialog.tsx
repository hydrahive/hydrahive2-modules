/** G1: neue Geschichte, obwohl es schon Szenen gibt – ersetzen, anhängen oder abbrechen (eigener Dialog, kein Browser-Popup). */
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Backdrop } from "../StudioDialogs"

interface Props { count: number; busy: boolean; onReplace: () => void; onAppend: () => void; onClose: () => void }

export function ReplaceDialog({ count, busy, onReplace, onAppend, onClose }: Props) {
  const { t } = useTranslation("studio")
  return (
    <Backdrop onClose={onClose} label={t("guided.replace_title")}>
      <div className="space-y-4 p-5">
        <h2 className="text-lg font-black text-[#f2f6fc]">{t("guided.replace_title")}</h2>
        <p className="text-base text-[#c3ccdd]">{t("guided.replace_text", { count })}</p>
        <div className="flex flex-wrap justify-end gap-2">
          <button type="button" onClick={onReplace} disabled={busy}
            className="flex items-center gap-2 rounded-[8px] bg-[#3ddc97] px-4 py-2 text-sm font-bold text-[#04140d] disabled:opacity-50">
            {busy && <Loader2 size={14} className="animate-spin" />}{t("guided.replace_yes")}
          </button>
          <button type="button" onClick={onAppend} disabled={busy}
            className="rounded-[8px] border border-[#46617f] px-4 py-2 text-sm font-bold text-[#e8eef8] hover:bg-[#1c2940] disabled:opacity-50">{t("guided.replace_append")}</button>
          <button type="button" onClick={onClose} className="rounded-[8px] px-4 py-2 text-sm text-[#8d9ab0] hover:text-[#e8eef8]">{t("cancel")}</button>
        </div>
      </div>
    </Backdrop>
  )
}
