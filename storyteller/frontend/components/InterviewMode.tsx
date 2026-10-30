// KI-Modus „Interview“ (Ghostwriter G3, Spec §10): Für das Kapitel der aktuellen Szene Fragen vorschlagen lassen,
// beantworten (tippen oder diktieren), dann das Kapitel aus den Antworten schreiben lassen (Lauf wie G2).
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { BookOpenText, Loader2, MessageCircleQuestion, Trash2 } from "lucide-react"
import { StoryApiError } from "../api"
import { overLimit, totalTokens } from "../costLimit"
import { interviewApi } from "../interviewApi"
import type { RunEstimate } from "../runApi"
import { addQuestions, answeredCount, appendDictation, editAnswer, editQuestion, MAX_QUESTIONS, removeQuestion } from "../interviewModel"
import { findScene, type Scene } from "../model"
import type { BookState } from "../useBook"
import { useGhostRun } from "../useGhostRun"
import { useInterview } from "../useInterview"
import { DictateButton } from "./DictateButton"
import { RunProgress } from "./RunProgress"

const field = "w-full rounded border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1 text-sm text-[#e8eef8] placeholder:text-[#9aa7bc]"

interface Props { state: BookState; scene: Scene; onOpenScene: (id: string) => void }

export function InterviewMode({ state, scene, onOpenScene }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const { projectId, book, canWrite } = state
  const chapter = findScene(book, scene.id)?.chapter
  const cid = chapter?.id ?? ""
  const iv = useInterview(projectId, book.id, cid)
  const run = useGhostRun(state)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [est, setEst] = useState<RunEstimate | null>(null)   // Schätzung zum Bestätigen (null = noch nicht gefragt)
  const answered = answeredCount(iv.questions)
  const fail = (e: unknown) => setError(e instanceof StoryApiError ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e))

  const suggest = async () => {
    setBusy(true); setError("")
    try {
      await iv.flush()
      const r = await interviewApi.suggest(projectId, book.id, cid, Math.min(6, MAX_QUESTIONS - iv.questions.length) || 1)
      iv.change(addQuestions(iv.questions, r.questions))
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const req = { scope: "chapter" as const, chapter_id: cid, skip_filled: true, source: "interview" as const }
  const over = overLimit(est, est?.limit_tokens ?? 0)
  const prepare = async () => {
    setError("")
    await iv.flush()
    try { setEst(await run.estimate(req)) } catch (e) { fail(e) }
  }
  const write = async () => {
    if (await run.start(req, over)) setEst(null)
  }

  if (!chapter) return null
  return (
    <div className="st-interview space-y-3">
      <p className="text-xs text-[#c8d2df]">{t("interview_intro", { chapter: chapter.title })}</p>
      {iv.state === "conflict" && (
        <div className="rounded border border-amber-400/30 bg-amber-400/5 px-2 py-1.5 text-xs text-amber-200">
          <p>{t("interview_conflict")}</p>
          <div className="mt-1 flex gap-2">
            <button className="underline" onClick={() => { void iv.resolve("reload") }}>{t("conflict_reload")}</button>
            <button className="underline" onClick={() => { void iv.resolve("keep") }}>{t("conflict_keep")}</button>
          </div>
        </div>
      )}
      {iv.state === "failed" && <p className="text-xs text-red-300" role="alert">{t("interview_save_failed")} <button className="underline" onClick={() => { void iv.retry() }}>{t("save_retry")}</button></p>}
      <p className="st-interview-count text-xs text-[#c8d2df]">{t("interview_count", { answered, total: iv.questions.length })}</p>
      <ol className="space-y-3">
        {iv.questions.map((q, i) => (
          <li key={q.id} className="space-y-1 rounded border border-[rgb(var(--hh-s-rand,42_54_75))] p-2">
            <div className="flex items-start gap-1">
              <span className="pt-1 text-xs text-[#9aa7bc]">{i + 1}.</span>
              <input className={`${field} font-semibold`} value={q.question} readOnly={!canWrite} aria-label={t("interview_question")}
                onChange={(e) => iv.change(editQuestion(iv.questions, q.id, e.target.value))} />
              {canWrite && <button title={t("outline_remove")} onClick={() => iv.change(removeQuestion(iv.questions, q.id))} className="pt-1 text-[#9aa7bc] hover:text-red-300"><Trash2 className="h-3.5 w-3.5" /></button>}
            </div>
            <textarea className={`${field} min-h-[72px]`} value={q.answer} readOnly={!canWrite} placeholder={t("interview_answer_ph")}
              aria-label={t("interview_answer")} onChange={(e) => iv.change(editAnswer(iv.questions, q.id, e.target.value))} />
            {canWrite && <DictateButton onText={(text) => iv.change(appendDictation(iv.questions, q.id, text))} />}
          </li>
        ))}
      </ol>
      {canWrite && (
        <button onClick={() => { void suggest() }} disabled={busy || iv.questions.length >= MAX_QUESTIONS || iv.state === "loading"}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-2 text-sm text-[#e8eef8] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] disabled:opacity-40">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageCircleQuestion className="h-4 w-4" />}
          {iv.questions.length ? t("interview_more") : t("interview_suggest")}
        </button>
      )}
      {run.run && run.run.options?.source === "interview" && (
        <RunProgress run={run.run} book={book} canWrite={canWrite} onCancel={() => { void run.cancel() }} onOpenScene={onOpenScene} />
      )}
      {!run.active && !est && (
        <button onClick={() => { void prepare() }} disabled={!canWrite || answered === 0}
          className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-[#163248] px-3 py-2 text-sm font-semibold text-white hover:bg-[#1b3d56] disabled:opacity-40">
          <BookOpenText className="h-4 w-4" />{t("interview_write")}
        </button>
      )}
      {!run.active && est && (
        <div className="st-interview-confirm space-y-2 rounded-lg border border-[#69d7ff]/30 bg-[#69d7ff]/5 p-2 text-xs text-[#c8d2df]">
          <p>{t("interview_confirm", { scenes: est.scenes, total: totalTokens(est).toLocaleString(i18n.language), model: est.model || t("ghost_model_default") })}
            {est.cost_micros !== null && <> · {t("run_cost", { cents: (est.cost_micros / 1000).toFixed(2) })}</>}</p>
          {over && <p className="text-amber-200">{t("run_over_limit", { total: totalTokens(est).toLocaleString(i18n.language), limit: est.limit_tokens.toLocaleString(i18n.language) })}</p>}
          <div className="flex gap-2">
            <button onClick={() => { void write() }} className="flex-1 rounded-lg bg-[#163248] px-3 py-1.5 text-sm font-semibold text-white hover:bg-[#1b3d56]">
              {over ? t("run_start_over", { scenes: est.scenes }) : t("run_start", { scenes: est.scenes })}
            </button>
            <button onClick={() => setEst(null)} className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 text-sm">{t("ghost_stop")}</button>
          </div>
        </div>
      )}
      {answered === 0 && canWrite && <p className="text-[11px] text-[#9aa7bc]">{t("interview_need_answer")}</p>}
      {(error || run.error) && <p className="st-ai-error rounded border border-red-400/30 bg-red-500/10 px-2 py-1.5 text-xs text-red-200" role="alert">
        {error || t(`ai_err_${run.error?.code}`, { defaultValue: run.error?.message || run.error?.code })}</p>}
    </div>
  )
}
