import { Loader2, Square } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Job } from "./planApi"

/** Kopfzeile: laufender Sammelauftrag mit Fortschritt („Bilder: 3 von 8“), aktuellem Schritt und Abbrechen. */
export function BatchStatus({ job, cancelling, onCancel }: { job: Job; cancelling: boolean; onCancel: () => void }) {
  const { t } = useTranslation("studio")
  const p = job.progress ?? { total: 0, done: 0, failed: 0, current: "" }
  const pct = p.total ? Math.round(((p.done + p.failed) / p.total) * 100) : 0
  return (
    <div className="flex min-w-0 items-center gap-2 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-1 text-[11px] text-[#c3ccdd]" data-batch-status={job.kind}>
      <Loader2 size={12} className="shrink-0 animate-spin text-[#ffb86b]" />
      <span className="shrink-0 font-bold">{t(`batch_progress.${job.kind}`, { done: p.done, total: p.total })}</span>
      <span className="h-1 w-16 shrink-0 overflow-hidden rounded-full bg-[#1c2940]"><span className="block h-full bg-[#69d7ff]" style={{ width: `${pct}%` }} /></span>
      {p.current && <span className="min-w-0 truncate text-[#9aa7bc]" title={p.current}>{p.current}</span>}
      {p.failed > 0 && <span className="shrink-0 text-[#ff6b8a]">{t("batch_failed", { count: p.failed })}</span>}
      <button type="button" onClick={onCancel} disabled={cancelling} data-batch-cancel title={t("batch_cancel_hint")}
        className="flex shrink-0 items-center gap-1 rounded px-1 text-[#9aa7bc] hover:text-[#ff6b8a] disabled:opacity-50">
        <Square size={10} /> {cancelling ? t("batch_cancelling") : t("batch_cancel")}
      </button>
    </div>
  )
}
