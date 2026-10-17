import { useRef } from "react"
import { Magnet, Scissors, ZoomIn, ZoomOut } from "lucide-react"
import { useTranslation } from "react-i18next"
import { DEMO_DURATION, DEMO_TRACKS, type DemoTrack, type TrackKind } from "./demoData"
import { centerAt, tickStep, toFraction, zoom, type Viewport } from "./timeline"
import { TrackRow } from "./TrackRow"

interface Props {
  time: number
  view: Viewport
  snap: boolean
  selected: string | null
  /** Ton-Arbeitsbereich: Tonspuren groß, Videospuren klein. */
  focus: "all" | "audio" | "subtitles"
  onView: (v: Viewport) => void
  onSeek: (t: number) => void
  onSelect: (clipId: string) => void
  onSnap: () => void
}

const AUDIO: TrackKind[] = ["voice", "music"]

/** Zeitleiste: Übersicht (ganzer Film) + gezoomter Ausschnitt mit Spuren (Spec „Oberfläche“). */
export function TimelinePanel({ time, view, snap, selected, focus, onView, onSeek, onSelect, onSnap }: Props) {
  const { t } = useTranslation("studio")
  const laneRef = useRef<HTMLDivElement>(null)
  const step = tickStep(view.span)
  const ticks: number[] = []
  for (let s = Math.ceil(view.start / step) * step; s <= view.start + view.span; s += step) ticks.push(s)

  const fractionOf = (clientX: number, el: HTMLElement | null) => {
    const r = el?.getBoundingClientRect()
    return r && r.width ? Math.min(1, Math.max(0, (clientX - r.left) / r.width)) : 0
  }
  const big = (tr: DemoTrack) => focus === "all" || (focus === "audio" ? AUDIO.includes(tr.kind) : tr.kind === "subtitle")

  return (
    <section className="flex h-full min-h-0 flex-col" data-studio-panel="timeline">
      <div className="flex h-8 shrink-0 items-center gap-1 border-b border-[#2a364b] px-2 text-[#8d9ab0]">
        <button type="button" className="rounded-[4px] p-1 hover:bg-[#111827]" title={t("split")}><Scissors size={13} /></button>
        <button type="button" onClick={onSnap} aria-pressed={snap} data-studio-action="snap" title={t("snap")}
          className={`rounded-[4px] p-1 ${snap ? "text-[#69d7ff]" : ""} hover:bg-[#111827]`}><Magnet size={13} /></button>
        <span className="mx-2 h-4 w-px bg-[#2a364b]" />
        <button type="button" className="rounded-[4px] p-1 hover:bg-[#111827]" title={t("zoom_in")} onClick={() => onView(zoom(view, 0.7, toFraction(time, view), DEMO_DURATION))}><ZoomIn size={13} /></button>
        <button type="button" className="rounded-[4px] p-1 hover:bg-[#111827]" title={t("zoom_out")} onClick={() => onView(zoom(view, 1.4, toFraction(time, view), DEMO_DURATION))}><ZoomOut size={13} /></button>
        <span className="ml-auto text-[10px]">{t("overview_hint")}</span>
      </div>
      {/* Übersicht: ganzer Film, Rahmen = sichtbarer Ausschnitt */}
      <div className="relative mx-2 mt-1.5 h-4 shrink-0 cursor-pointer rounded-[3px] bg-[#111827]" data-studio-overview
        onPointerDown={(e) => onView(centerAt(view, fractionOf(e.clientX, e.currentTarget), DEMO_DURATION))}>
        {DEMO_TRACKS.find((tr) => tr.kind === "video")?.clips.map((c) => (
          <span key={c.id} className={`absolute top-1 h-2 rounded-[2px] ${c.placeholder ? "bg-[#ffb86b]/60" : "bg-[#46617f]"}`}
            style={{ left: `${(c.start / DEMO_DURATION) * 100}%`, width: `${(c.length / DEMO_DURATION) * 100}%` }} />
        ))}
        <span className="absolute inset-y-0 rounded-[3px] border border-[#69d7ff] bg-[#69d7ff]/10"
          style={{ left: `${(view.start / DEMO_DURATION) * 100}%`, width: `${(view.span / DEMO_DURATION) * 100}%` }} />
        <span className="absolute inset-y-0 w-px bg-[#ff6b8a]" style={{ left: `${(time / DEMO_DURATION) * 100}%` }} />
      </div>
      <div className="relative mt-1 min-h-0 flex-1 overflow-y-auto">
        <div className="flex h-5 border-b border-[#1e2738] pl-24 text-[10px] text-[#3f4b60]">
          <div className="relative flex-1 cursor-pointer" onPointerDown={(e) => onSeek(view.start + fractionOf(e.clientX, e.currentTarget) * view.span)}>
            {ticks.map((s) => <span key={s} className="absolute top-0.5" style={{ left: `${toFraction(s, view) * 100}%` }}>{s}s</span>)}
          </div>
        </div>
        <div ref={laneRef} className="relative">
          {DEMO_TRACKS.map((tr) => (
            <TrackRow key={tr.id} track={tr} view={view} big={big(tr)} selected={selected} onSelect={onSelect} />
          ))}
          <div className="pointer-events-none absolute inset-y-0 left-24 right-0">
            {toFraction(time, view) >= 0 && toFraction(time, view) <= 1 && (
              <span className="absolute inset-y-0 w-px bg-[#ff6b8a]" data-studio-playhead style={{ left: `${toFraction(time, view) * 100}%` }} />
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
