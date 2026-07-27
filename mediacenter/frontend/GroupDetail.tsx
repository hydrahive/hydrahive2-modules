import { ArrowLeft, Check, Download, ShieldX, Star } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { errorMessage, mediacenterApi } from "./api"
import { formatBytes, reasonLabel } from "./format"
import { ArrHandoffButton } from "./ArrHandoffButton"
import type { ModuleStatus, ResultGroup, SearchResult } from "./types"

interface Props {
  group: ResultGroup
  onBack: () => void
  onQueued: () => void
  status: ModuleStatus | null
}

/**
 * Detailansicht eines Titels: Backdrop, Handlung, Genre, Bewertung — darunter
 * alle gefundenen Fassungen.
 *
 * Die Freigabe-Logik stammt unverändert aus V1: nur `decision === "eligible"`
 * mit `result_id` lässt sich herunterladen; abgelehnte Fassungen bleiben
 * sichtbar (mit Begründung), aber ohne Knopf.
 */
export function GroupDetail({ group, onBack, onQueued, status }: Props) {
  const { t } = useTranslation("mediacenter")
  const [pending, setPending] = useState<string | null>(null)
  const [queued, setQueued] = useState<Set<string>>(new Set())
  const [actionError, setActionError] = useState<string | null>(null)

  const enqueue = async (release: SearchResult) => {
    if (!release.result_id) return
    setPending(release.result_id)
    setActionError(null)
    try {
      await mediacenterApi.enqueue(release.result_id)
      setQueued((current) => new Set(current).add(release.result_id as string))
      onQueued()
    } catch (cause) {
      setActionError(errorMessage(cause))
    } finally {
      setPending(null)
    }
  }

  return <section className="space-y-4">
    <button type="button" onClick={onBack}
      className="flex items-center gap-2 text-xs font-bold text-[#8d9ab0] transition hover:text-cyan-200">
      <ArrowLeft size={14} />{t("results.back")}
    </button>

    <div className="overflow-hidden rounded-[6px] border border-[#28354a] bg-[#101724]">
      {group.backdrop_url && <div className="relative h-40 w-full overflow-hidden sm:h-56">
        <img src={group.backdrop_url} alt="" referrerPolicy="no-referrer"
          className="h-full w-full object-cover opacity-60" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#101724] via-[#101724]/40 to-transparent" />
      </div>}
      <div className="flex gap-4 p-4">
        {group.cover_url && <img src={group.cover_url} alt="" referrerPolicy="no-referrer"
          className="hidden w-28 shrink-0 self-start rounded-[4px] border border-[#28354a] sm:block" />}
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-black tracking-tight text-[#e8eef8]">{group.title}</h2>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[#8d9ab0]">
            {group.year !== null && <span>{group.year}</span>}
            {group.rating !== null && <span className="flex items-center gap-1 text-amber-300">
              <Star size={11} className="fill-amber-300" />{group.rating.toFixed(1)}
            </span>}
            <span>{t(`media.${group.media_type}`)}</span>
          </p>
          {group.genres.length > 0 && <div className="mt-2 flex flex-wrap gap-1.5">
            {group.genres.map((genre) => <span key={genre}
              className="rounded-full bg-white/[6%] px-2 py-0.5 text-[10px] font-semibold text-[#a9b6c9]">{genre}</span>)}
          </div>}
          {group.plot && <p className="mt-3 text-xs leading-relaxed text-[#a9b6c9]">{group.plot}</p>}
        </div>
      </div>
    </div>

    {actionError && <p className="rounded-[4px] border border-rose-500/25 bg-rose-500/[8%] p-3 text-xs text-rose-200" role="alert">{actionError}</p>}

    <h3 className="text-xs font-bold uppercase tracking-wider text-[#8d9ab0]">
      {t("results.versionsHeading", { count: group.releases.length })}
    </h3>
    <div className="space-y-2">
      {group.releases.map((release, index) => {
        const allowed = release.decision === "eligible" && Boolean(release.result_id)
        const isQueued = release.result_id ? queued.has(release.result_id) : false
        const preference = release.selection_status === "ready" ? null : t(`selection.${release.selection_status}`)
        return <article key={release.result_id ?? `${release.title}-${index}`}
          className={`rounded-[6px] border p-3 ${allowed ? "border-[#2d4255] bg-[#101724]" : "border-rose-500/20 bg-rose-500/[5%]"}`}>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0 flex-1">
              <div className="flex items-start gap-2">
                {allowed ? <Check size={15} className="mt-0.5 shrink-0 text-emerald-300" />
                  : <ShieldX size={15} className="mt-0.5 shrink-0 text-rose-300" />}
                <div className="min-w-0">
                  <p className="break-words text-xs font-semibold text-[#e8eef8]">{release.title}</p>
                  <p className="mt-1 text-[11px] text-[#8d9ab0]">
                    {[formatBytes(release.size_bytes),
                      release.age_days === null ? null : t("results.days", { count: release.age_days }),
                      release.language, release.resolution, release.format,
                      release.bitrate_kbps ? `${release.bitrate_kbps} kbit/s` : null,
                      `Score ${release.score}`].filter(Boolean).join(" · ")}
                  </p>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {release.reasons.map((reason) => <span key={reason}
                  className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${allowed ? "bg-emerald-400/10 text-emerald-200" : "bg-rose-400/10 text-rose-200"}`}>
                  {t(`reasons.${reason}`, { defaultValue: reasonLabel(reason) })}
                </span>)}
              </div>
              {preference && allowed && <p className="mt-2 text-[11px] text-amber-200">{preference}. {t("results.directChoice")}</p>}
            </div>
            {allowed && <div className="flex shrink-0 flex-col items-stretch gap-2">
              {/* Zwei Wege: verwaltet über Radarr/Sonarr (bevorzugt, kennt die
                  Bibliothek) oder direkt an SABnzbd. */}
              <ArrHandoffButton release={release} status={status} />
              <button type="button" onClick={() => enqueue(release)}
                disabled={pending === release.result_id || isQueued}
                className="flex items-center justify-center gap-2 rounded-[4px] bg-cyan-400/20 px-3 py-2 text-xs font-bold text-cyan-100 ring-1 ring-cyan-400/50 transition hover:bg-cyan-400/30 disabled:cursor-not-allowed disabled:opacity-50">
                {isQueued ? <Check size={14} /> : <Download size={14} />}
                {isQueued ? t("results.queued") : pending === release.result_id ? t("results.enqueueing") : t("results.enqueue")}
              </button>
            </div>}
          </div>
        </article>
      })}
    </div>
  </section>
}
