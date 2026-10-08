// T1e – Team-Knöpfe im Reiter „Team“: einen Helfer ohne Chat beauftragen. Erst Schätzung zeigen, dann starten.
// Laufende Aufträge mit Stoppen; fertige mit tatsächlichen Kosten. Fragt nur nach, solange etwas läuft; wird ein
// Auftrag fertig, werden die Hinweise neu geladen (dort steht sein Ergebnis). Ohne Schreibrecht: nur die Liste.
// Kostengrenze (A1): gleiche Einstellung wie beim Ghostwriter; über der Grenze nur mit „Trotzdem starten“.
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, Square, Users } from "lucide-react"
import { StoryApiError } from "../api"
import { totalTokens } from "../costLimit"
import { costLabel } from "../runView"
import { notesApi } from "../teamNotes"
import { activeFor, isActive, jobsApi, JOB_POLL_MS, needsPolling, placeFor,
  type CatalogEntry, type JobEstimate, type TeamJob } from "../teamJobs"
import type { BookState } from "../useBook"
import { LimitField } from "./LimitField"

interface Props { state: BookState; sceneId: string }

export function TeamJobs({ state, sceneId }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const n = (v: number) => v.toLocaleString(i18n.language)
  const { projectId, book, canWrite, setNotes } = state
  const [catalog, setCatalog] = useState<CatalogEntry[]>([])
  const [jobs, setJobs] = useState<TeamJob[] | null>(null)
  const [pending, setPending] = useState<{ entry: CatalogEntry; est: JobEstimate } | null>(null)
  const [error, setError] = useState("")
  const activeBefore = useRef<Set<string>>(new Set())
  const chapters = useMemo(() => Object.fromEntries(
    book.parts.flatMap((p) => p.chapters.map((c) => [c.id, c.scenes.map((s) => s.id)]))), [book])

  const fail = useCallback((e: unknown) => setError(e instanceof StoryApiError
    ? t(`ai_err_${e.code}`, { defaultValue: e.message || e.code }) : String(e)), [t])

  const refresh = useCallback(async () => {
    const list = await jobsApi.list(projectId, book.id)
    const nowActive = new Set(list.filter(isActive).map((j) => j.id))
    const finished = [...activeBefore.current].some((id) => !nowActive.has(id))
    activeBefore.current = nowActive
    setJobs(list)
    if (finished) setNotes(await notesApi.list(projectId, book.id))   // Ergebnis des Helfers sofort sichtbar
  }, [projectId, book.id, setNotes])

  useEffect(() => {
    let alive = true
    Promise.all([jobsApi.catalog(projectId, book.id), jobsApi.list(projectId, book.id)])
      .then(([cat, list]) => {
        if (!alive) return
        setCatalog(cat); setJobs(list)
        activeBefore.current = new Set(list.filter(isActive).map((j) => j.id))
      })
      .catch((e: unknown) => { if (alive) fail(e) })
    return () => { alive = false }
  }, [projectId, book.id, fail])

  const polling = needsPolling(jobs)
  useEffect(() => {
    if (!polling) return
    const timer = window.setInterval(() => { refresh().catch(() => { /* nächste Abfrage */ }) }, JOB_POLL_MS)
    return () => window.clearInterval(timer)
  }, [polling, refresh])

  // Eine offene Bestätigung gilt nur für die Grenze, mit der geschätzt wurde – sonst neu auf einen Knopf klicken.
  const limit = book.ghost.limit_tokens || 0
  const confirm = pending && pending.est.limit_tokens === limit ? pending : null

  const ask = async (entry: CatalogEntry) => {
    const place = placeFor(entry.scope, sceneId, chapters)
    if (!place) return
    setError("")
    try { setPending({ entry, est: await jobsApi.estimate(projectId, book.id, entry.key, place) }) } catch (e) { fail(e) }
  }
  const start = async () => {
    if (!confirm) return
    try {
      const job = await jobsApi.start(projectId, book.id, confirm.entry.key, confirm.est.place_id, confirm.est.over_limit)
      activeBefore.current.add(job.id)
      setJobs((l) => [job, ...(l ?? [])])
      setPending(null)
    } catch (e) { fail(e); setPending(null) }
  }
  const stop = async (job: TeamJob) => {
    try { await jobsApi.cancel(projectId, book.id, job.id); await refresh() } catch (e) { fail(e) }
  }

  const cost = confirm ? costLabel(confirm.est.cost_micros, false) : null
  const list = jobs ?? []
  return (
    <section className="st-team-jobs space-y-2 rounded-lg border border-white/10 bg-zinc-900/40 p-2">
      <h3 className="flex items-center gap-1.5 text-xs font-medium text-zinc-300"><Users className="h-3.5 w-3.5" />{t("job_heading")}</h3>
      {canWrite && <>
        <p className="text-[11px] text-zinc-500">{t("job_hint")}</p>
        <div className="flex flex-wrap gap-1">
          {catalog.map((c) => {
            const place = placeFor(c.scope, sceneId, chapters)
            const running = place ? activeFor(list, c.key, place) : undefined
            return (
              <button key={c.key} disabled={!c.available || !place || !!running || !!confirm}
                title={c.available ? t(`job_scope_${c.scope}`) : t("job_unavailable")} onClick={() => { void ask(c) }}
                className="st-job-button rounded border border-white/10 px-2 py-0.5 text-xs text-zinc-200 hover:bg-white/10 disabled:opacity-40">
                {running && <Loader2 className="mr-1 inline h-3 w-3 animate-spin" />}{t(`job_${c.key}`, { defaultValue: c.label })}
              </button>
            )
          })}
        </div>
        {confirm && (
          <div className="st-job-confirm space-y-1 rounded border border-violet-400/30 bg-violet-500/10 p-2 text-xs" role="dialog">
            <p className="text-zinc-100">{t("job_confirm", { label: t(`job_${confirm.entry.key}`), place: confirm.est.place_title })}</p>
            <p className="text-zinc-400">{cost ? t("job_estimate", { total: n(totalTokens(confirm.est)), cents: cost.cents, model: confirm.est.model })
              : t("job_estimate_unknown", { total: n(totalTokens(confirm.est)), model: confirm.est.model })}</p>
            {confirm.est.over_limit && <p className="st-job-over text-amber-200">
              {t("run_over_limit", { total: n(totalTokens(confirm.est)), limit: n(confirm.est.limit_tokens) })}</p>}
            <div className="flex gap-2">
              <button onClick={() => { void start() }} className="rounded bg-violet-600 px-2 py-0.5 text-white">
                {confirm.est.over_limit ? t("job_start_over") : t("job_start")}</button>
              <button onClick={() => setPending(null)} className="rounded px-2 py-0.5 text-zinc-300 hover:bg-white/10">{t("job_cancel_confirm")}</button>
            </div>
          </div>
        )}
      </>}
      <LimitField state={state} price={confirm?.est ?? null} />
      {error && <p className="text-xs text-red-200" role="alert">{error}</p>}
      {list.length > 0 && <JobList jobs={list.slice(0, 5)} canWrite={canWrite} onStop={(j) => { void stop(j) }} />}
    </section>
  )
}

function JobList({ jobs, canWrite, onStop }: { jobs: TeamJob[]; canWrite: boolean; onStop: (j: TeamJob) => void }) {
  const { t } = useTranslation("storyteller")
  return (
    <ul className="space-y-1 text-[11px]" aria-label={t("job_recent")}>
      {jobs.map((j) => {
        const cost = costLabel(j.cost_micros, false)
        return (
          <li key={j.id} className={`st-job st-job-${j.status} flex items-center gap-1.5 text-zinc-400`}>
            {isActive(j) && <Loader2 className="h-3 w-3 shrink-0 animate-spin text-violet-300" />}
            <span className="min-w-0 flex-1 truncate" title={j.summary || j.error || j.place_title}>
              {t(`job_${j.job}`, { defaultValue: j.job })} · {j.place_title}
            </span>
            <span className={j.status === "error" ? "text-red-300" : j.status === "done" ? "text-emerald-300"
              : j.status === "limit" ? "text-amber-300" : ""}>
              {t(`job_${j.status}`)}{cost && j.status !== "queued" ? ` · ${t("job_cost", { cents: cost.cents })}` : ""}
            </span>
            {j.session_id && !isActive(j) && <a href={`/werkstatt/${j.session_id}`} target="_blank" rel="noopener noreferrer"
              className="text-sky-300 hover:underline">{t("job_open_session")}</a>}
            {canWrite && isActive(j) && <button onClick={() => onStop(j)} aria-label={t("job_stop")}
              className="rounded p-0.5 text-zinc-400 hover:bg-white/10 hover:text-red-200"><Square className="h-3 w-3" /></button>}
          </li>
        )
      })}
    </ul>
  )
}
