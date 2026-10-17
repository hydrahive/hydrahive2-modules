import { Clapperboard, Film, Image as ImageIcon, Loader2, Sparkles, ZoomIn, ZoomOut } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { clipLength, filmLength } from "./cutLogic"
import { fileOf } from "./planLogic"
import { centerAt, tickStep, toFraction, zoom, type Viewport } from "./timeline"
import { clipsOf, type Timeline, type TimelineClip } from "./timelineApi"

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
}

const pct = (n: number) => `${Math.round(n * 1e6) / 1e4}%`
const fractionOf = (clientX: number, el: HTMLElement) => {
  const r = el.getBoundingClientRect()
  return r.width ? Math.min(1, Math.max(0, (clientX - r.left) / r.width)) : 0
}

/** Reiter „Schneiden“: echte Zeitleiste (Spur V1) mit Übersichtsleiste, Zoom und Abspielkopf (Etappe 4a). */
export function CutTimeline({ timeline, base, time, view, selected, busy, onView, onSeek, onSelect, onFromPlan }: Props) {
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
            <div className="relative flex h-16 border-b border-[#1e2738]" data-studio-track="video">
              <div className="flex w-24 shrink-0 items-center gap-1 border-r border-[#1e2738] bg-[#0d1420] px-2 text-[10px] font-bold text-[#8d9ab0]">V1 {t("cut_track_video")}</div>
              <div className="relative min-w-0 flex-1 overflow-hidden" onPointerDown={(e) => { if (e.target === e.currentTarget) onSeek(view.start + fractionOf(e.clientX, e.currentTarget) * view.span) }}>
                {clips.map((c) => <ClipBlock key={c.id} clip={c} base={base} view={view} active={c.id === selected} onSelect={onSelect} />)}
                {toFraction(time, view) >= 0 && toFraction(time, view) <= 1 && (
                  <span className="pointer-events-none absolute inset-y-0 w-px bg-[#ff6b8a]" data-studio-playhead style={{ left: pct(toFraction(time, view)) }} />
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  )
}

function ClipBlock({ clip, base, view, active, onSelect }: { clip: TimelineClip; base: string; view: Viewport; active: boolean; onSelect: (id: string) => void }) {
  const left = toFraction(clip.start, view)
  const width = clipLength(clip) / view.span
  if (left + width < 0 || left > 1) return null
  const ph = clip.kind === "placeholder"
  const img = clip.kind === "image" ? fileOf(base, clip.media_rel) : ""
  return (
    <button type="button" data-cut-clip={clip.id} data-placeholder={ph ? "1" : undefined} onClick={() => onSelect(clip.id)} title={clip.label}
      className={`absolute inset-y-1.5 flex items-center gap-1 overflow-hidden rounded-[3px] px-1.5 text-left text-[10px] text-white
        ${ph ? `border border-dashed ${clip.missing ? "border-[#ff6b8a] bg-[#ff6b8a]/10 text-[#ff6b8a]" : "border-[#ffb86b] bg-[#ffb86b]/10 text-[#ffb86b]"}`
        : clip.kind === "image" ? "bg-[#3d5a80]" : "bg-[#2f6aa8]"} ${active ? "ring-2 ring-[#69d7ff]" : ""}`}
      style={{ left: pct(left), width: pct(width) }}>
      {img && <img src={fileUrl(img)} alt="" loading="lazy" className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-35" />}
      <span className="relative flex min-w-0 items-center gap-1">
        {ph ? <Sparkles size={10} className="shrink-0" /> : clip.kind === "image" ? <ImageIcon size={10} className="shrink-0" /> : <Film size={10} className="shrink-0" />}
        <span className="truncate">{clip.label}</span>
      </span>
    </button>
  )
}
