import { Clapperboard, Loader2, ZoomIn, ZoomOut } from "lucide-react"
import { useTranslation } from "react-i18next"
import { clipLength, filmLength } from "./cutLogic"
import { pct } from "./cutDnd"
import { CutTrack, type TrackEdit } from "./CutTrack"
import { centerAt, tickStep, toFraction, zoom, type Viewport } from "./timeline"
import { clipsOf, type Timeline } from "./timelineApi"

interface Props {
  timeline: Timeline | null
  base: string
  time: number
  view: Viewport
  selected: string | null
  busy: boolean
  onView: (v: Viewport) => void
  onSeek: (t: number) => void
  onSelect: (id: string) => void
  onFromPlan: () => void
  /** Werkzeugleiste (4b) und Bearbeiten; ohne nur Ansehen. */
  toolbar?: React.ReactNode
  edit?: TrackEdit
}

const fractionOf = (clientX: number, el: HTMLElement) => {
  const r = el.getBoundingClientRect()
  return r.width ? Math.min(1, Math.max(0, (clientX - r.left) / r.width)) : 0
}

/** Reiter „Schneiden“: echte Zeitleiste (Spur V1) mit Übersichtsleiste, Zoom und Abspielkopf (Etappe 4a). */
export function CutTimeline({ timeline, base, time, view, selected, busy, onView, onSeek, onSelect, onFromPlan, toolbar, edit }: Props) {
  const { t } = useTranslation("studio")
  const clips = clipsOf(timeline)
  const total = Math.max(filmLength(clips), 1)
  const step = tickStep(view.span)
  const ticks: number[] = []
  for (let s = Math.ceil(view.start / step) * step; s <= view.start + view.span; s += step) ticks.push(s)
  const fromPlan = (
    <button type="button" onClick={onFromPlan} disabled={busy} data-cut-from-plan title={t("cut_from_plan_hint")}
      className="flex shrink-0 items-center gap-1.5 rounded-[4px] border border-[#46617f] px-2 py-0.5 font-bold text-[#69d7ff] hover:bg-[#1c2940] disabled:opacity-50">
      {busy ? <Loader2 size={12} className="animate-spin" /> : <Clapperboard size={12} />} {t("cut_from_plan")}
    </button>
  )
  return (
    <section className="flex h-full min-h-0 flex-col" data-studio-panel="timeline" data-cut-length={Math.round(filmLength(clips) * 100) / 100}>
      <div className="flex h-8 shrink-0 items-center gap-1 border-b border-[#2a364b] px-2 text-[11px] text-[#8d9ab0]">
        <button type="button" className="rounded-[4px] p-1 hover:bg-[#111827]" title={t("zoom_in")} onClick={() => onView(zoom(view, 0.7, toFraction(time, view), total))}><ZoomIn size={13} /></button>
        <button type="button" className="rounded-[4px] p-1 hover:bg-[#111827]" title={t("zoom_out")} onClick={() => onView(zoom(view, 1.4, toFraction(time, view), total))}><ZoomOut size={13} /></button>
        <span className="ml-1 truncate">{t("cut_count", { count: clips.length })}</span>
        {toolbar}
        <span className="ml-auto" />
        {fromPlan}
      </div>
      {!clips.length ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 p-4 text-center text-xs text-[#68758a]">
          <p className="max-w-md leading-relaxed">{t("cut_empty")}</p>
        </div>
      ) : (
        <>
          <div className="relative mx-2 mt-1.5 h-4 shrink-0 cursor-pointer rounded-[3px] bg-[#111827]" data-studio-overview
            onPointerDown={(e) => onView(centerAt(view, fractionOf(e.clientX, e.currentTarget), total))}>
            {clips.map((c) => (
              <span key={c.id} className={`absolute top-1 h-2 rounded-[2px] ${c.kind === "placeholder" ? "bg-[#ffb86b]/60" : "bg-[#46617f]"}`}
                style={{ left: pct(c.start / total), width: pct(clipLength(c) / total) }} />
            ))}
            <span className="absolute inset-y-0 rounded-[3px] border border-[#69d7ff] bg-[#69d7ff]/10" style={{ left: pct(view.start / total), width: pct(view.span / total) }} />
            <span className="absolute inset-y-0 w-px bg-[#ff6b8a]" style={{ left: pct(time / total) }} />
          </div>
          <div className="relative mt-1 min-h-0 flex-1 overflow-y-auto">
            <div className="flex h-5 border-b border-[#1e2738] pl-24 text-[10px] text-[#3f4b60]">
              <div className="relative flex-1 cursor-pointer overflow-hidden" data-cut-ruler onPointerDown={(e) => onSeek(view.start + fractionOf(e.clientX, e.currentTarget) * view.span)}>
                {ticks.filter((s) => toFraction(s, view) < 0.97).map((s) => <span key={s} className="absolute top-0.5" style={{ left: pct(toFraction(s, view)) }}>{s}s</span>)}
              </div>
            </div>
            <CutTrack clips={clips} base={base} view={view} time={time} selected={selected} edit={edit} onSelect={onSelect} onSeek={onSeek} />
          </div>
        </>
      )}
    </section>
  )
}
