import { ArrowRight, Download, Film, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { deliverSummary, filmSize, minutes } from "./deliverLogic"
import { jobText } from "./jobLogic"
import type { Job } from "./planApi"
import type { RenderItem } from "./renderApi"
import type { TimelineClip } from "./timelineApi"

interface Props {
  clips: TimelineClip[]
  aspect: string
  renders: RenderItem[]
  job: Job | null
  busy: boolean
  onRender: () => void
  onCut: () => void
}

/** Reiter „Ausgabe“ (4d): Film als MP4 erzeugen, fertige Filme ansehen und herunterladen. */
export function DeliverPanel({ clips, aspect, renders, job, busy, onRender, onCut }: Props) {
  const { t } = useTranslation("studio")
  const sum = deliverSummary(clips)
  const [w, h] = filmSize(aspect)
  const running = job?.status === "running" || job?.status === "queued"
  return (
    <section className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto p-4 text-xs text-[#c3ccdd]" data-studio-panel="deliver">
      <div className="space-y-2 rounded-[6px] border border-[#46617f] bg-[#0e1420] p-3">
        {!sum.clips ? (
          <>
            <p data-deliver-empty>{t("deliver_empty")}</p>
            <button type="button" onClick={onCut} className="flex items-center gap-1.5 rounded-[4px] border border-[#46617f] px-2.5 py-1 font-bold text-[#69d7ff] hover:bg-[#1c2940]">
              {t("soon_to_cut")} <ArrowRight size={12} />
            </button>
          </>
        ) : (
          <>
            <p className="text-sm text-[#e8eef8]">{t("deliver_summary", { length: minutes(sum.seconds), clips: sum.clips, width: w, height: h })}</p>
            {sum.placeholders > 0 && <p className="text-[#ffb86b]">{t("deliver_placeholders", { count: sum.placeholders })}</p>}
            <p className="text-[#8d9ab0]">{t("deliver_hint")}</p>
          </>
        )}
        <button type="button" onClick={onRender} disabled={busy || running || !sum.clips} data-deliver-run
          className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
          {running ? <Loader2 size={13} className="animate-spin" /> : <Film size={13} />} {t("deliver_run")}
        </button>
        {running && <p className="text-[#ffb86b]" data-deliver-progress>{t("deliver_running", { percent: job?.progress?.done ?? 0 })}</p>}
        {job?.status === "failed" && <p className="text-[#ff6b8a]" data-deliver-error>{jobText(t, job)}</p>}
      </div>
      <h3 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">{t("deliver_films")}</h3>
      {!renders.length ? <p className="text-[#68758a]">{t("deliver_none")}</p> : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-3">
          {renders.map((r) => (
            <figure key={r.rel} className="space-y-1.5 rounded-[6px] border border-[#2a364b] bg-[#0d1420] p-2" data-deliver-film={r.rel}>
              <video src={fileUrl(r.abs)} controls preload="metadata" className="aspect-video w-full rounded-[3px] bg-black object-contain" />
              <figcaption className="space-y-1">
                <p className="text-[#e8eef8]">{(r.created_at || "").slice(0, 16).replace("T", " ")}</p>
                <p className="text-[#8d9ab0]">{t("deliver_film_info", { length: minutes(r.duration ?? 0), width: r.width, height: r.height })}</p>
                {!!r.missing && <p className="text-[#ffb86b]">{t("deliver_missing", { count: r.missing })}</p>}
                <a href={fileUrl(r.abs)} download={`film-${(r.created_at || r.name).slice(0, 16).replace(/[^0-9]/g, "")}.mp4`}
                  className="inline-flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 font-bold text-[#69d7ff] hover:border-[#69d7ff] hover:bg-[#1c2940]">
                  <Download size={12} /> {t("deliver_download")}
                </a>
              </figcaption>
            </figure>
          ))}
        </div>
      )}
    </section>
  )
}
