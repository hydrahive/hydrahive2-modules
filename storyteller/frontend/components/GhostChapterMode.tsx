// KI-Modus „Kapitel/Buch“ (Ghostwriter G2, Spec §9): Umfang wählen (dieses Kapitel / ab hier / ganzes
// Buch), Schätzung ansehen, bestätigen, Lauf im Hintergrund verfolgen. Darunter: Gliederung aus Idee.
// Kostengrenze je Buch (0 = keine): ohne Grenze muss jede Schätzung bestätigt werden.
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { BookOpenText } from "lucide-react"
import { allScenes, findScene, type Scene } from "../model"
import type { RunEstimate, RunRequest, RunScope } from "../runApi"
import { costLabel } from "../runView"
import type { BookState } from "../useBook"
import { useGhostRun } from "../useGhostRun"
import { OutlinePanel } from "./OutlinePanel"
import { OutlineProposalBox } from "./OutlineProposalBox"
import { RunProgress } from "./RunProgress"

const field = "rounded-lg border border-white/10 bg-zinc-950 px-2 py-1 text-sm text-zinc-100"

interface Props { state: BookState; scene: Scene; onOpenScene: (id: string) => void }

export function GhostChapterMode({ state, scene, onOpenScene }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const { book, canWrite, flush } = state
  const run = useGhostRun(state)
  const { estimate, active } = run
  const [scope, setScope] = useState<RunScope>("chapter")
  const [skipFilled, setSkipFilled] = useState(true)
  const [est, setEst] = useState<RunEstimate | null>(null)
  const [estError, setEstError] = useState("")
  const [limit, setLimit] = useState(book.ghost.limit_tokens || 0)
  const chapterId = findScene(book, scene.id)?.chapter.id
  const req: RunRequest = { scope, skip_filled: skipFilled,
    ...(scope === "chapter" ? { chapter_id: chapterId } : scope === "from" ? { scene_id: scene.id } : {}) }
  const reqKey = JSON.stringify(req)
  // Schätzung hängt an Zusammenfassungen, „hat Text“ und den Buch-Einstellungen – nicht an jedem Tastendruck.
  const bookKey = JSON.stringify([book.ghost, book.model, allScenes(book).map(({ scene: s }) => [s.id, s.summary, !!s.text.trim()])])
  const n = (v: number) => v.toLocaleString(i18n.language)

  useEffect(() => {
    if (active) return
    let alive = true
    const timer = setTimeout(() => {
      void flush().then(() => estimate(JSON.parse(reqKey) as RunRequest))
        .then((e) => { if (alive) { setEst(e); setEstError("") } })
        .catch((e) => { if (alive) { setEst(null); setEstError(String(e?.code ?? e)) } })
    }, 400)
    return () => { alive = false; clearTimeout(timer) }
    // Neu schätzen, wenn sich Umfang/Option, die Zusammenfassungen/Einstellungen oder der Lauf ändern.
  }, [reqKey, bookKey, active, estimate, flush])

  const over = !!est && !!book.ghost.limit_tokens && est.output_tokens > book.ghost.limit_tokens
  const cost = est ? costLabel(est.cost_micros, false) : null
  const saveLimit = () => state.change((b) => ({ ...b, ghost: { ...b.ghost, limit_tokens: limit } }))

  return (
    <div className="st-ghost-chapter space-y-3">
      <p className="text-xs text-zinc-400">{t("run_intro")}</p>
      {run.run && <RunProgress run={run.run} book={book} canWrite={canWrite} onCancel={() => { void run.cancel() }} onOpenScene={onOpenScene} />}
      {!run.active && (
        <fieldset className="space-y-2 text-xs text-zinc-400" disabled={!canWrite}>
          <legend className="mb-1">{t("run_scope")}</legend>
          <div className="flex flex-wrap gap-1" role="radiogroup">
            {(["chapter", "from", "book"] as const).map((s) => (
              <button key={s} type="button" role="radio" aria-checked={scope === s} onClick={() => setScope(s)}
                className={`rounded-lg border px-2 py-1 ${scope === s ? "border-violet-400 bg-violet-500/15 text-violet-100" : "border-white/10 hover:bg-white/5"}`}>
                {t(`run_scope_${s}`)}
              </button>
            ))}
          </div>
          <label className="flex items-center gap-2"><input type="checkbox" checked={skipFilled} onChange={(e) => setSkipFilled(e.target.checked)} />{t("run_skip_filled")}</label>
          <label className="flex items-center gap-2">{t("run_limit")}
            <input type="number" min={0} step={1000} value={limit || ""} placeholder={t("run_limit_none")} className={`${field} w-28`}
              onChange={(e) => setLimit(Number(e.target.value) || 0)} onBlur={() => { if (limit !== book.ghost.limit_tokens && (limit === 0 || (limit >= 1000 && limit <= 2_000_000))) saveLimit() }} />
          </label>
          {est && (
            <p className="st-run-estimate text-[11px] text-zinc-400">
              {t("run_estimate", { scenes: est.scenes, out: n(est.output_tokens), in: n(est.input_tokens), model: est.model || t("ghost_model_default") })}
              {cost && <> · {t("run_cost", { cents: cost.cents })}</>}
              {(est.skipped_filled > 0 || est.skipped_no_summary > 0) && <> · {t("run_skipped", { filled: est.skipped_filled, nosum: est.skipped_no_summary })}</>}
            </p>
          )}
          {estError && <p className="text-xs text-red-300">{t(`ai_err_${estError}`, { defaultValue: estError })}</p>}
          {over && <p className="st-run-over rounded border border-amber-400/30 bg-amber-400/5 px-2 py-1 text-amber-200">{t("run_over_limit")}</p>}
          <button onClick={() => { void run.start(req, over) }} disabled={!est || est.scenes === 0}
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-40">
            <BookOpenText className="h-4 w-4" />{over ? t("run_start_over", { scenes: est?.scenes ?? 0 }) : t("run_start", { scenes: est?.scenes ?? 0 })}
          </button>
        </fieldset>
      )}
      {run.error && <p className="st-ai-error rounded border border-red-400/30 bg-red-500/10 px-2 py-1.5 text-xs text-red-200" role="alert">
        {t(`ai_err_${run.error.code}`, { defaultValue: run.error.message || run.error.code })}</p>}
      {!run.active && state.outlineProposal && <OutlineProposalBox key={state.outlineProposal.at} state={state} proposal={state.outlineProposal} />}
      {!run.active && <OutlinePanel state={state} />}
    </div>
  )
}
