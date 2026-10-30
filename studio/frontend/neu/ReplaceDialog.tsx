/** G1: neue Geschichte, obwohl es schon Szenen gibt – ersetzen, anhängen oder abbrechen (eigener Dialog, kein Browser-Popup). */
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Backdrop } from "../StudioDialogs"

interface Props {
  count: number; busy: boolean; onReplace: () => void; onAppend: () => void; onClose: () => void
  /** G5: dieselbe Rückfrage mit eigenen Texten (Hand-Schnitt) */
  title?: string; text?: string; yes?: string; other?: string
}

export function ReplaceDialog({ count, busy, onReplace, onAppend, onClose, title, text, yes, other }: Props) {
  const { t } = useTranslation("studio")
  const head = title ?? t("guided.replace_title")
  return (
    <Backdrop onClose={onClose} label={head}>
      <div className="space-y-4 p-5">
        <h2 className="text-lg font-black text-[#f2f6fc]">{head}</h2>
        <p className="text-base text-[#c3ccdd]">{text ?? t("guided.replace_text", { count })}</p>
        <div className="flex flex-wrap justify-end gap-2">
          <button type="button" onClick={onReplace} disabled={busy}
            className="flex items-center gap-2 rounded-[8px] bg-[#3ddc97] px-4 py-2 text-sm font-bold text-[#04140d] disabled:opacity-50">
            {busy && <Loader2 size={14} className="animate-spin" />}{yes ?? t("guided.replace_yes")}
          </button>
          <button type="button" onClick={onAppend} disabled={busy}
            className="rounded-[8px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] px-4 py-2 text-sm font-bold text-[#e8eef8] hover:bg-[#1c2940] disabled:opacity-50">{other ?? t("guided.replace_append")}</button>
          <button type="button" onClick={onClose} className="rounded-[8px] px-4 py-2 text-sm text-[#9aa7bc] hover:text-[#e8eef8]">{t("cancel")}</button>
        </div>
      </div>
    </Backdrop>
  )
}
