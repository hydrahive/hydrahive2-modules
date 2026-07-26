import { Clock3, RefreshCw } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { errorMessage, mediacenterApi } from "./api"
import { formatDate, formatSpeed } from "./format"
import type { Job } from "./types"

interface Props {
  mode: "queue" | "history"
  refreshKey?: number
}

export function JobsPanel({ mode, refreshKey = 0 }: Props) {
  const { t } = useTranslation("mediacenter")
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setJobs(mode === "queue" ? await mediacenterApi.queue() : await mediacenterApi.history())
    } catch (cause) {
      setError(errorMessage(cause))
    } finally {
      setLoading(false)
    }
  }, [mode])

  useEffect(() => { void load() }, [load, refreshKey])
  useEffect(() => {
    if (mode !== "queue") return
    const timer = window.setInterval(() => { void load() }, 10_000)
    return () => window.clearInterval(timer)
  }, [load, mode])

  return <section className="space-y-3" aria-label={t(`jobs.${mode}`)}>
    <div className="flex items-center justify-between gap-3">
      <div>
        <h2 className="text-sm font-bold text-[#e8eef8]">{t(`jobs.${mode}`)}</h2>
        <p className="mt-1 text-xs text-[#78869d]">{t(`jobs.${mode}Hint`)}</p>
      </div>
      <button type="button" onClick={() => void load()} disabled={loading}
        className="flex items-center gap-2 rounded-[4px] border border-[#34445d] bg-[#151e2d] px-3 py-2 text-xs font-bold text-[#d4deeb] hover:border-cyan-400/60 disabled:opacity-40">
        <RefreshCw size={13} className={loading ? "animate-spin" : ""} />{t("jobs.refresh")}
      </button>
    </div>
    {error && <p className="rounded-[4px] border border-rose-500/25 bg-rose-500/[8%] p-3 text-xs text-rose-200" role="alert">{error}</p>}
    {jobs === null && loading ? <Empty text={t("jobs.loading")} /> : jobs?.length === 0 ? <Empty text={t(`jobs.${mode}Empty`)} /> : jobs?.map((job) => <JobCard key={job.result_id} job={job} />)}
  </section>
}

function JobCard({ job }: { job: Job }) {
  const { t } = useTranslation("mediacenter")
  const speed = formatSpeed(job.speed_kbps)
  return <article className="rounded-[6px] border border-[#2d3b51] bg-[#101724] p-4">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h3 className="break-words text-sm font-bold text-[#e8eef8]">{job.title}</h3>
        <p className="mt-1 text-xs text-[#78869d]">{t(`media.${job.media_type}`)} · {formatDate(job.updated_at)}</p>
      </div>
      <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${job.status === "failed" || job.error_code ? "bg-rose-400/10 text-rose-200" : job.status === "completed" ? "bg-emerald-400/10 text-emerald-200" : "bg-cyan-400/10 text-cyan-200"}`}>{t(`status.${job.status}`, { defaultValue: job.status })}</span>
    </div>
    {job.progress !== null && <div className="mt-3">
      <div className="mb-1 flex justify-between text-[10px] text-[#8d9ab0]"><span>{job.progress.toFixed(1)}%</span><span>{[speed, job.eta ? `${t("jobs.eta")} ${job.eta}` : null].filter(Boolean).join(" · ")}</span></div>
      <div className="h-1.5 overflow-hidden rounded-full bg-[#202b3d]"><div className="h-full rounded-full bg-cyan-400" style={{ width: `${Math.max(0, Math.min(job.progress, 100))}%` }} /></div>
    </div>}
    {job.progress === null && <p className="mt-3 flex items-center gap-2 text-xs text-[#8d9ab0]"><Clock3 size={13} />{job.state}</p>}
    {job.error_code && <p className="mt-3 text-xs text-rose-200">{t(`errors.${job.error_code}`, { defaultValue: job.error_code })}</p>}
  </article>
}

function Empty({ text }: { text: string }) {
  return <div className="rounded-[6px] border border-dashed border-[#2b394f] bg-[#0d141f] px-4 py-10 text-center text-sm text-[#78869d]">{text}</div>
}
