import { Download, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { ImportPreview } from "./planApi"
import { importAmounts } from "./planLogic"
import { Backdrop } from "./StudioDialogs"

interface Props {
  preview: ImportPreview
  busy: boolean
  onRun: () => void
  onClose: () => void
}

/** Übernahme aus dem Atelier: zeigt vorher, was kopiert wird. Das Atelier bleibt unverändert. */
export function ImportDialog({ preview, busy, onRun, onClose }: Props) {
  const { t } = useTranslation("studio")
  return (
    <Backdrop onClose={onClose} label={t("import_title")}>
      <div className="space-y-3 p-4 text-xs text-[#c3ccdd]" data-import-dialog>
        <h3 className="text-sm font-black text-[#e8eef8]">{t("import_title")}</h3>
        <p>{t("import_counts", importAmounts(t, preview))}</p>
        {preview.look && <p>{t("import_look")}</p>}
        <p className="rounded-[4px] border border-[#46617f] bg-[#111827] px-2.5 py-2 leading-relaxed text-[#8d9ab0]">{t("import_hint")}</p>
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#8d9ab0] hover:text-[#e8eef8]">{t("cancel")}</button>
          <button type="button" onClick={onRun} disabled={busy} data-import-run
            className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />} {t("import_run")}
          </button>
        </div>
      </div>
    </Backdrop>
  )
}
