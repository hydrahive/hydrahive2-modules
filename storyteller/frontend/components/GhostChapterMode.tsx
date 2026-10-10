// KI-Modus „Kapitel/Buch“ (Ghostwriter G2, Spec §9): Umfang wählen (dieses Kapitel / ab hier / ganzes
// Buch), Schätzung ansehen, bestätigen, Lauf im Hintergrund verfolgen. Darunter: Gliederung aus Idee.
// Kostengrenze je Auftrag (A1, LimitField): Eingabe + Ausgabe; liegt die Schätzung darüber → „Trotzdem“.
// C2: Schalter „Autor darf die Gliederung direkt ändern“ und Kasten mit dem Umbau-Vorschlag des Autors.
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { BookOpenText } from "lucide-react"
import { overLimit, totalTokens } from "../costLimit"
import { allScenes, findScene, type Scene } from "../model"
import type { RunEstimate, RunRequest, RunScope } from "../runApi"
import { costLabel } from "../runView"
import type { BookState } from "../useBook"
import { useGhostRun } from "../useGhostRun"
import { LimitField } from "./LimitField"
import { OutlinePanel } from "./OutlinePanel"
import { OutlineProposalBox } from "./OutlineProposalBox"
import { RestructureProposalBox } from "./RestructureProposalBox"
import { RunProgress } from "./RunProgress"
import { StructureSwitch } from "./StructureSwitch"


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

  const limit = book.ghost.limit_tokens || 0
  const over = overLimit(est, limit)
  const cost = est ? costLabel(est.cost_micros, false) : null

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
          {est && (
            <p className="st-run-estimate text-[11px] text-zinc-400">
              {t("run_estimate", { scenes: est.scenes, total: n(totalTokens(est)), out: n(est.output_tokens), in: n(est.input_tokens), model: est.model || t("ghost_model_default") })}
              {cost && <> · {t("run_cost", { cents: cost.cents })}</>}
              {(est.skipped_filled > 0 || est.skipped_no_summary > 0) && <> · {t("run_skipped", { filled: est.skipped_filled, nosum: est.skipped_no_summary })}</>}
            </p>
          )}
          {estError && <p className="text-xs text-red-300">{t(`ai_err_${estError}`, { defaultValue: estError })}</p>}
          {over && est && <p className="st-run-over rounded border border-amber-400/30 bg-amber-400/5 px-2 py-1 text-amber-200">
            {t("run_over_limit", { total: n(totalTokens(est)), limit: n(limit) })}</p>}
          <button onClick={() => { void run.start(req, over) }} disabled={!est || est.scenes === 0}
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-40">
            <BookOpenText className="h-4 w-4" />{over ? t("run_start_over", { scenes: est?.scenes ?? 0 }) : t("run_start", { scenes: est?.scenes ?? 0 })}
          </button>
        </fieldset>
      )}
      {!run.active && <LimitField state={state} price={est} />}
      {!run.active && <StructureSwitch state={state} />}
      {run.error && <p className="st-ai-error rounded border border-red-400/30 bg-red-500/10 px-2 py-1.5 text-xs text-red-200" role="alert">
        {t(`ai_err_${run.error.code}`, { defaultValue: run.error.message || run.error.code })}</p>}
      {!run.active && state.restructureProposal && <RestructureProposalBox key={state.restructureProposal.at} state={state} proposal={state.restructureProposal} />}
      {!run.active && state.outlineProposal && <OutlineProposalBox key={state.outlineProposal.at} state={state} proposal={state.outlineProposal} />}
      {!run.active && <OutlinePanel state={state} />}
    </div>
  )
}
