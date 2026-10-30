import { Layers, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { BatchKind, BatchPreview } from "./planApi"
import { Backdrop } from "./StudioDialogs"
import { Costs } from "./Costs"

interface Props {
  kind: BatchKind
  preview: BatchPreview | null
  busy: boolean
  onRun: () => void
  onClose: () => void
}

/** Rückfrage vor einem Sammelauftrag: was passiert, wie oft, mit welchem Modell (kein Browser-Popup). */
export function BatchDialog({ kind, preview, busy, onRun, onClose }: Props) {
  const { t } = useTranslation("studio")
  return (
    <Backdrop onClose={onClose} label={t(`batch_title.${kind}`)}>
      <div className="space-y-3 p-4 text-xs text-[#c3ccdd]" data-batch-dialog={kind}>
        <h3 className="text-sm font-black text-[#e8eef8]">{t(`batch_title.${kind}`)}</h3>
        {!preview ? <p className="flex items-center gap-1.5 text-[#9aa7bc]"><Loader2 size={12} className="animate-spin" /> {t("loading")}</p>
          : preview.count === 0 ? <p>{t(`batch_nothing.${kind}`)}</p>
            : (
              <>
                <p className="text-sm text-[#e8eef8]">{t(`batch_question.${kind}`, { count: preview.count, model: preview.model })}</p>
                <p className="rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2.5 py-2 leading-relaxed text-[#9aa7bc]">{t("batch_hint")}</p>
              </>
            )}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#9aa7bc] hover:text-[#e8eef8]">{t("cancel")}</button>
          {preview && preview.count > 0 && (
            <button type="button" onClick={onRun} disabled={busy} data-batch-run
              className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Layers size={13} />} {t("batch_run")}
             <Costs model={preview?.model} />
        </button>
          )}
        </div>
      </div>
    </Backdrop>
  )
}
