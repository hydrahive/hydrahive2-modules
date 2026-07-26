import { Check, Download, ShieldX } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { errorMessage, mediacenterApi } from "./api"
import { formatBytes, reasonLabel } from "./format"
import type { SearchResponse, SearchResult } from "./types"

interface Props {
  response: SearchResponse | null
  searched: boolean
  error: string | null
  onQueued: () => void
}

export function ResultList({ response, searched, error, onQueued }: Props) {
  const { t } = useTranslation("mediacenter")
  const [pending, setPending] = useState<string | null>(null)
  const [queued, setQueued] = useState<Set<string>>(new Set())
  const [actionError, setActionError] = useState<string | null>(null)

  const enqueue = async (result: SearchResult) => {
    if (!result.result_id) return
    setPending(result.result_id)
    setActionError(null)
    try {
      await mediacenterApi.enqueue(result.result_id)
      setQueued((current) => new Set(current).add(result.result_id as string))
      onQueued()
    } catch (cause) {
      setActionError(errorMessage(cause))
    } finally {
      setPending(null)
    }
  }

  if (error) return <div className="rounded-[6px] border border-rose-500/25 bg-rose-500/[8%] p-4 text-sm text-rose-200" role="alert">{error}</div>
  if (!searched) return <Empty text={t("results.initial")} />
  if (!response?.results.length) return <Empty text={t("results.empty")} />

  return <section className="space-y-3" aria-label={t("results.title")}>
    <div className="flex items-center justify-between gap-3 text-xs text-[#8d9ab0]">
      <span>{t("results.summary", { total: response.total, eligible: response.eligible })}</span>
      <span>{t("results.expiry")}</span>
    </div>
    {actionError && <p className="rounded-[4px] border border-rose-500/25 bg-rose-500/[8%] p-3 text-xs text-rose-200" role="alert">{actionError}</p>}
    {response.results.map((result, index) => {
      const allowed = result.decision === "eligible" && Boolean(result.result_id)
      const isQueued = result.result_id ? queued.has(result.result_id) : false
      const preference = result.selection_status === "ready" ? null : t(`selection.${result.selection_status}`)
      return <article key={result.result_id ?? `${result.title}-${index}`}
        className={`rounded-[6px] border p-4 ${allowed ? "border-[#2d4255] bg-[#101724]" : "border-rose-500/20 bg-rose-500/[5%]"}`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-start gap-2">
              {allowed ? <Check size={16} className="mt-0.5 shrink-0 text-emerald-300" /> : <ShieldX size={16} className="mt-0.5 shrink-0 text-rose-300" />}
              <div className="min-w-0">
                <h3 className="break-words text-sm font-bold text-[#e8eef8]">{result.title}</h3>
                <p className="mt-1 text-xs text-[#8d9ab0]">
                  {[formatBytes(result.size_bytes), result.age_days === null ? null : t("results.days", { count: result.age_days }), result.language, result.resolution, result.format, result.bitrate_kbps ? `${result.bitrate_kbps} kbit/s` : null, `Score ${result.score}`].filter(Boolean).join(" · ")}
                </p>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {result.reasons.map((reason) => <span key={reason} className={`rounded-full px-2 py-1 text-[10px] font-semibold ${allowed ? "bg-emerald-400/10 text-emerald-200" : "bg-rose-400/10 text-rose-200"}`}>{t(`reasons.${reason}`, { defaultValue: reasonLabel(reason) })}</span>)}
            </div>
            {preference && allowed && <p className="mt-3 text-xs text-amber-200">{preference}. {t("results.directChoice")}</p>}
          </div>
          {allowed && <button type="button" onClick={() => enqueue(result)} disabled={pending === result.result_id || isQueued}
            className="flex shrink-0 items-center justify-center gap-2 rounded-[4px] bg-cyan-400/20 px-3 py-2 text-xs font-bold text-cyan-100 ring-1 ring-cyan-400/50 transition hover:bg-cyan-400/30 disabled:cursor-not-allowed disabled:opacity-50">
            {isQueued ? <Check size={14} /> : <Download size={14} />}
            {isQueued ? t("results.queued") : pending === result.result_id ? t("results.enqueueing") : t("results.enqueue")}
          </button>}
        </div>
      </article>
    })}
  </section>
}

function Empty({ text }: { text: string }) {
  return <div className="rounded-[6px] border border-dashed border-[#2b394f] bg-[#0d141f] px-4 py-10 text-center text-sm text-[#78869d]">{text}</div>
}
