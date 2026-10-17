import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { CutClip } from "./CutClip"
import { CLIP_MIME, MEDIA_MIME, pct } from "./cutDnd"
import { insertAt, snapEdge } from "./cutEdit"
import { clipLength } from "./cutLogic"
import { toFraction, type Viewport } from "./timeline"
import type { TimelineClip } from "./timelineApi"

/** Was die Spur zum Bearbeiten braucht (ohne: nur ansehen wie in 4a). */
export interface TrackEdit {
  onMove: (id: string, index: number) => void
  /** Kürzen: Rand um `delta` Sekunden gegenüber dem Stand beim Greifen; `final` = losgelassen (ein Verlaufsschritt). */
  onTrim: (id: string, edge: "start" | "end", delta: number, final: boolean) => void
  onDrop: (mediaId: string, index: number) => void
  /** Einfügemarke (Filmzeit) beim Ziehen – von außen gesetzt, damit die Anzeige testbar ist. */
  dropAt: number | null
  /** Ziele fürs Einrasten (z. B. Abspielkopf); leer = aus. */
  snapTo: number[]
}

interface Props {
  clips: TimelineClip[]
  base: string
  view: Viewport
  time: number
  selected: string | null
  edit?: TrackEdit
  onSelect: (id: string) => void
  onSeek: (t: number) => void
}

const timeAt = (el: HTMLElement, clientX: number, view: Viewport) => {
  const r = el.getBoundingClientRect()
  return view.start + (r.width ? Math.min(1, Math.max(0, (clientX - r.left) / r.width)) : 0) * view.span
}

/** Spur V1: Clips, Abspielkopf, Ziehen zum Umsortieren, Ablage aus der Bibliothek, Kürzen an den Rändern. */
export function CutTrack({ clips, base, view, time, selected, edit, onSelect, onSeek }: Props) {
  const { t } = useTranslation("studio")
  const lane = useRef<HTMLDivElement>(null)
  const [drag, setDrag] = useState<number | null>(null)
  const marker = edit?.dropAt ?? drag
  const markerT = marker === null ? null : (() => {
    const sorted = [...clips].sort((a, b) => a.start - b.start)
    const i = insertAt(sorted, marker)
    return i < sorted.length ? sorted[i].start : sorted.length ? sorted[sorted.length - 1].start + clipLength(sorted[sorted.length - 1]) : 0
  })()

  const startTrim = (id: string, edge: "start" | "end", x0: number) => {
    const el = lane.current
    if (!el || !edit) return
    const c = clips.find((x) => x.id === id)
    if (!c) return
    const edgeT = edge === "start" ? c.start : c.start + clipLength(c)
    const perPx = view.span / (el.getBoundingClientRect().width || 1)
    const delta = (x: number) => {
      const raw = edgeT + (x - x0) * perPx
      const snapped = snapEdge(raw, edit.snapTo, view.span, el.getBoundingClientRect().width)
      return snapped - edgeT
    }
    const move = (e: PointerEvent) => edit.onTrim(id, edge, delta(e.clientX), false)
    const up = (e: PointerEvent) => {
      window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up)
      edit.onTrim(id, edge, delta(e.clientX), true)
    }
    window.addEventListener("pointermove", move)
    window.addEventListener("pointerup", up)
  }

  return (
    <div className="relative flex h-16 border-b border-[#1e2738]" data-studio-track="video">
      <div className="flex w-24 shrink-0 items-center gap-1 border-r border-[#1e2738] bg-[#0d1420] px-2 text-[10px] font-bold text-[#8d9ab0]">V1 {t("cut_track_video")}</div>
      <div ref={lane} className="relative min-w-0 flex-1 overflow-hidden" data-cut-dropzone={edit ? "1" : undefined}
        onPointerDown={(e) => { if (e.target === e.currentTarget) onSeek(timeAt(e.currentTarget, e.clientX, view)) }}
        onDragOver={(e) => {
          if (!edit) return
          const types = [...e.dataTransfer.types]
          if (!types.includes(CLIP_MIME) && !types.includes(MEDIA_MIME)) return
          e.preventDefault()
          setDrag(timeAt(e.currentTarget, e.clientX, view))
        }}
        onDragLeave={() => setDrag(null)}
        onDrop={(e) => {
          if (!edit) return
          e.preventDefault()
          const at = insertAt(clips, timeAt(e.currentTarget, e.clientX, view))
          const clipId = e.dataTransfer.getData(CLIP_MIME)
          const mediaId = e.dataTransfer.getData(MEDIA_MIME)
          setDrag(null)
          if (clipId) {
            const from = [...clips].sort((a, b) => a.start - b.start).findIndex((c) => c.id === clipId)
            edit.onMove(clipId, from >= 0 && at > from ? at - 1 : at)             // Index in der Liste ohne den Clip
          } else if (mediaId) edit.onDrop(mediaId, at)
        }}>
        {clips.map((c) => <CutClip key={c.id} clip={c} base={base} view={view} active={c.id === selected} editable={!!edit}
          onSelect={onSelect} onTrimStart={startTrim} />)}
        {markerT !== null && toFraction(markerT, view) >= 0 && toFraction(markerT, view) <= 1 && (
          <span className="pointer-events-none absolute inset-y-0 z-20 w-0.5 bg-[#ffb86b]" data-cut-insert style={{ left: pct(toFraction(markerT, view)) }} />
        )}
        {toFraction(time, view) >= 0 && toFraction(time, view) <= 1 && (
          <span className="pointer-events-none absolute inset-y-0 w-px bg-[#ff6b8a]" data-studio-playhead style={{ left: pct(toFraction(time, view)) }} />
        )}
      </div>
    </div>
  )
}
