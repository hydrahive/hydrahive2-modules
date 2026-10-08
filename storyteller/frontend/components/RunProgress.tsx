// Ghostwriter G2 – Fortschritt eines Laufs: Balken, Zahlen, aktuelle Szene, Tokens/Kosten, Abbrechen.
import { useTranslation } from "react-i18next"
import { Loader2, Square } from "lucide-react"
import { findScene, type Book } from "../model"
import { costLabel, isFinished, progressCounts, type RunInfo } from "../runView"

interface Props { run: RunInfo; book: Book; canWrite: boolean; onCancel: () => void; onOpenScene: (id: string) => void }

export function RunProgress({ run, book, canWrite, onCancel, onOpenScene }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const c = progressCounts(run)
  const done = c.total - c.open
  const finished = isFinished(run)
  const cost = costLabel(run.cost_micros, run.cost_partial)
  const current = run.current_scene ? findScene(book, run.current_scene)?.scene.title : null
  const n = (v: number) => v.toLocaleString(i18n.language)
  return (
    <section className="st-run space-y-2 rounded-xl border border-violet-400/30 bg-violet-500/5 p-3" aria-live="polite">
      <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-300">
        {!finished && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
        {t(`run_status_${run.status}`)}
      </h3>
      <div className="h-1.5 overflow-hidden rounded bg-white/10" role="progressbar" aria-valuemin={0} aria-valuemax={c.total} aria-valuenow={done}>
        <div className="h-full bg-violet-400 transition-all" style={{ width: `${c.total ? (done / c.total) * 100 : 0}%` }} />
      </div>
      <p className="st-run-counts text-xs text-zinc-300">
        {t("run_counts", { done, total: c.total, written: c.written, proposals: c.proposals, skipped: c.skipped, words: n(c.words) })}
      </p>
      {current && !finished && <p className="text-xs text-zinc-400">{t("run_current", { title: current })}</p>}
      <p className="text-[11px] text-zinc-500">
        {t("run_tokens", { total: n(run.tokens_in + run.tokens_out), out: n(run.tokens_out), in: n(run.tokens_in) })}
        {cost && <> · {t(cost.partial ? "run_cost_partial" : "run_cost", { cents: cost.cents })}</>}
      </p>
      {run.error && <p className="st-ai-error rounded border border-red-400/30 bg-red-500/10 px-2 py-1 text-xs text-red-200" role="alert">{run.error}</p>}
      {c.proposals > 0 && finished && <p className="text-xs text-amber-200">{t("run_proposals_hint", { count: c.proposals })}</p>}
      {c.errors > 0 && (
        <ul className="text-xs text-red-300">
          {run.progress.filter((p) => p.state === "error").map((p) => (
            <li key={p.scene_id}><button className="underline" onClick={() => onOpenScene(p.scene_id)}>
              {findScene(book, p.scene_id)?.scene.title ?? p.scene_id}</button></li>
          ))}
        </ul>
      )}
      {!finished && canWrite && (
        <button onClick={onCancel} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-1.5 text-sm text-zinc-200 hover:bg-white/5">
          <Square className="h-4 w-4" />{t("ghost_stop")}
        </button>
      )}
    </section>
  )
}
