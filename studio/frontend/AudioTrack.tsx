import { AudioLines, Mic, Music, VolumeX } from "lucide-react"
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import type { AudioTrack as TrackId } from "./cutAudio"
import { CLIP_MIME, MEDIA_MIME, pct } from "./cutDnd"
import { snapEdge } from "./cutEdit"
import { clipLength } from "./cutLogic"
import { toFraction, type Viewport } from "./timeline"
import type { TimelineClip } from "./timelineApi"
import { Waveform } from "./Waveform"

/** Was eine Tonspur zum Bearbeiten braucht (ohne: nur ansehen). */
export interface AudioEdit {
  /** Tonclip (auch von der anderen Tonspur) an die Zeit `start` legen. */
  onMove: (id: string, track: TrackId, start: number) => void
  onTrim: (id: string, edge: "start" | "end", delta: number, final: boolean) => void
  /** Medium aus der Bibliothek ab Zeit `start` auf diese Spur. */
  onDrop: (mediaId: string, track: TrackId, start: number) => void
  snapTo: number[]
  /** Ränder aller Clips aller Spuren (zum Einrasten beim Verschieben). */
  edges: number[]
}

interface Props {
  id: TrackId
  clips: TimelineClip[]
  view: Viewport
  time: number
  selected: string | null
  waveforms: Record<string, number[] | undefined>
  perSecond: number
  edit?: AudioEdit
  onSelect: (id: string) => void
  onSeek: (t: number) => void
  /** Stumm bzw. nicht im Solo (5b): blass, Hinweis im Spurkopf. */
  silent?: boolean
}

const timeAt = (el: HTMLElement, clientX: number, view: Viewport) => {
  const r = el.getBoundingClientRect()
  return view.start + (r.width ? Math.min(1, Math.max(0, (clientX - r.left) / r.width)) : 0) * view.span
}

/** Tonspur „Sprache“ (A1) oder „Musik“ (A2): Clips liegen frei, Lücken sind Stille (Spec „Bauplan Etappe 5“, 5a). */
export function AudioTrack({ id, clips, view, time, selected, waveforms, perSecond, edit, onSelect, onSeek, silent = false }: Props) {
  const { t } = useTranslation("studio")
  const lane = useRef<HTMLDivElement>(null)
  const grab = useRef<{ id: string; offset: number } | null>(null)    // Abstand Mauszeiger → Clipanfang beim Greifen
  const [over, setOver] = useState(false)
  const Icon = id === "A1" ? Mic : Music

  const startTrim = (cid: string, edge: "start" | "end", x0: number) => {
    const el = lane.current
    const c = clips.find((x) => x.id === cid)
    if (!el || !edit || !c) return
    const edgeT = edge === "start" ? c.start : c.start + clipLength(c)
    const w = el.getBoundingClientRect().width || 1
    const delta = (x: number) => snapEdge(edgeT + (x - x0) * (view.span / w), [...edit.snapTo, ...edit.edges], view.span, w) - edgeT
    const move = (e: PointerEvent) => edit.onTrim(cid, edge, delta(e.clientX), false)
    const up = (e: PointerEvent) => {
      window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up)
      edit.onTrim(cid, edge, delta(e.clientX), true)
    }
    window.addEventListener("pointermove", move)
    window.addEventListener("pointerup", up)
  }

  /** Ablagestelle: Clipanfang dort, wo er gegriffen wurde; eingerastet an Abspielkopf und Clipkanten. */
  const dropStart = (el: HTMLElement, clientX: number, clip?: TimelineClip) => {
    const raw = timeAt(el, clientX, view) - (grab.current?.offset ?? 0)
    if (!edit) return raw
    const w = el.getBoundingClientRect().width
    const targets = [...edit.snapTo, ...edit.edges.filter((e) => !clip || (e !== clip.start && e !== clip.start + clipLength(clip)))]
    const head = snapEdge(raw, targets, view.span, w)
    if (head !== raw || !clip) return head
    const tail = snapEdge(raw + clipLength(clip), targets, view.span, w)
    return tail - clipLength(clip)
  }

  return (
    <div className={`relative flex h-12 border-b border-[#1e2738] ${silent ? "opacity-45" : ""}`} data-studio-track={id === "A1" ? "voice" : "music"}
      data-track-silent={silent ? "1" : undefined}>
      <div className="flex w-24 shrink-0 items-center gap-1 border-r border-[#1e2738] bg-[#0d1420] px-2 text-[10px] font-bold text-[#8d9ab0]"
        title={silent ? t("mix_track_silent") : undefined}>
        {silent ? <VolumeX size={11} className="shrink-0 text-[#ff6b8a]" /> : <Icon size={11} className="shrink-0" />} {id} {t(id === "A1" ? "cut_track_voice" : "cut_track_music")}
      </div>
      <div ref={lane} className={`relative min-w-0 flex-1 overflow-hidden ${over ? "bg-[#2a7f62]/10" : ""}`} data-cut-audio-lane={id}
        onPointerDown={(e) => { if (e.target === e.currentTarget) onSeek(timeAt(e.currentTarget, e.clientX, view)) }}
        onDragOver={(e) => {
          if (!edit) return
          const types = [...e.dataTransfer.types]
          if (!types.includes(CLIP_MIME) && !types.includes(MEDIA_MIME)) return
          e.preventDefault()
          setOver(true)
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          if (!edit) return
          e.preventDefault()
          setOver(false)
          const clipId = e.dataTransfer.getData(CLIP_MIME)
          const mediaId = e.dataTransfer.getData(MEDIA_MIME)
          if (clipId) edit.onMove(clipId, id, Math.max(0, dropStart(e.currentTarget, e.clientX, clips.find((c) => c.id === clipId))))
          else if (mediaId) edit.onDrop(mediaId, id, Math.max(0, dropStart(e.currentTarget, e.clientX)))
          grab.current = null
        }}>
        {!clips.length && <span className="pointer-events-none absolute inset-0 flex items-center px-3 text-[10px] text-[#3f4b60]">{t("cut_audio_empty")}</span>}
        {clips.map((c) => {
          const left = toFraction(c.start, view)
          const width = clipLength(c) / view.span
          if (left + width < 0 || left > 1) return null
          const active = c.id === selected
          const grip = (edge: "start" | "end") => edit && (
            <span role="separator" aria-orientation="vertical" data-cut-trim={`${c.id}:${edge}`}
              onPointerDown={(e) => { e.stopPropagation(); e.preventDefault(); startTrim(c.id, edge, e.clientX) }}
              className={`absolute inset-y-0 z-10 w-1.5 cursor-ew-resize ${edge === "start" ? "left-0" : "right-0"} ${active ? "bg-[#7ee0b5]" : "hover:bg-[#7ee0b5]/70"}`} />
          )
          return (
            <div key={c.id} data-cut-clip={c.id} data-cut-audio={id} data-missing={c.missing ? "1" : undefined} draggable={!!edit} role="button" tabIndex={0} title={c.label}
              onClick={() => onSelect(c.id)} onKeyDown={(e) => { if (e.key === "Enter") onSelect(c.id) }}
              onDragStart={(e) => {
                const r = e.currentTarget.getBoundingClientRect()
                grab.current = { id: c.id, offset: r.width ? ((e.clientX - r.left) / r.width) * clipLength(c) : 0 }
                e.dataTransfer.setData(CLIP_MIME, c.id); e.dataTransfer.effectAllowed = "move"; onSelect(c.id)
              }}
              className={`absolute inset-y-1 flex cursor-grab items-center overflow-hidden rounded-[3px] px-2 text-[10px] text-white active:cursor-grabbing
                ${c.missing ? "border border-dashed border-[#ff6b8a] bg-[#ff6b8a]/10 text-[#ff6b8a]" : id === "A1" ? "bg-[#2a6f7f]" : "bg-[#2a7f62]"} ${active ? "ring-2 ring-[#7ee0b5]" : ""}`}
              style={{ left: pct(left), width: pct(width) }}>
              {!c.missing && <Waveform peaks={waveforms[c.media_rel]} perSecond={perSecond} from={c.in} to={c.out} />}
              <FadeMarks clip={c} />
              {grip("start")}
              <span className="pointer-events-none relative flex min-w-0 items-center gap-1">
                <AudioLines size={10} className="shrink-0" /><span className="truncate">{c.missing ? t("cut_audio_missing") : c.label}</span>
              </span>
              {grip("end")}
            </div>
          )
        })}
        {toFraction(time, view) >= 0 && toFraction(time, view) <= 1 && (
          <span className="pointer-events-none absolute inset-y-0 w-px bg-[#ff6b8a]" style={{ left: pct(toFraction(time, view)) }} />
        )}
      </div>
    </div>
  )
}

/** Blenden als dunkle Schräge am Clipanfang bzw. -ende (5b). */
function FadeMarks({ clip }: { clip: TimelineClip }) {
  const len = clipLength(clip)
  if (!len || (!clip.fade_in && !clip.fade_out)) return null
  const w = (s: number) => pct(Math.min(1, s / len))
  return <>
    {!!clip.fade_in && <span className="pointer-events-none absolute inset-y-0 left-0 bg-gradient-to-br from-black/55 from-50% to-transparent to-50%"
      style={{ width: w(clip.fade_in) }} data-fade="in" />}
    {!!clip.fade_out && <span className="pointer-events-none absolute inset-y-0 right-0 bg-gradient-to-bl from-black/55 from-50% to-transparent to-50%"
      style={{ width: w(clip.fade_out) }} data-fade="out" />}
  </>
}
