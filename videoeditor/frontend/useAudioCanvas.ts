import { useCallback, useRef } from "react"
import type { AudioTrack } from "./types"
import { timeAtX, type ViewState } from "./_timelineDraw"
import { hitAudioClip } from "./_audioDraw"

/** Was gerade am Canvas gezogen wird. */
type Drag =
  | { kind: "move"; trackId: string; clipId: string; grabDt: number }
  | { kind: "trim"; edge: "start" | "end"; trackId: string; clipId: string }
  | null

interface Deps {
  view: ViewState
  onViewChange: (updater: (v: ViewState) => ViewState) => void
  tracks: AudioTrack[]
  canvasRef: React.RefObject<HTMLCanvasElement | null>
  onSelectAudio: (sel: { trackId: string; clipId: string } | null) => void
  moveAudioClip: (trackId: string, clipId: string, tStart: number) => void
  trimAudioClip: (trackId: string, clipId: string, srcStart: number, srcEnd: number) => void
}

/** Pointer-/Wheel-Logik für den Audio-Canvas — Zoom/Scroll exakt wie
 *  TimelineCanvas (gemeinsame ViewState), plus Clip-Auswahl/Move/Trim.
 *  firstRowY ist 0: der Audio-Canvas beginnt direkt mit der ersten Spur. */
export function useAudioCanvas(d: Deps) {
  const { view, onViewChange, tracks, canvasRef, onSelectAudio, moveAudioClip, trimAudioClip } = d
  const dragRef = useRef<Drag>(null)

  const localXY = useCallback((e: React.PointerEvent): [number, number] => {
    const r = canvasRef.current!.getBoundingClientRect()
    return [e.clientX - r.left, e.clientY - r.top]
  }, [canvasRef])

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    const [x, y] = localXY(e)
    const hit = hitAudioClip(x, y, tracks, view, 0)
    if (!hit) { onSelectAudio(null); return }
    onSelectAudio({ trackId: hit.trackId, clipId: hit.clip.id })
    if (hit.edge) {
      dragRef.current = { kind: "trim", edge: hit.edge, trackId: hit.trackId, clipId: hit.clip.id }
    } else {
      dragRef.current = { kind: "move", trackId: hit.trackId, clipId: hit.clip.id, grabDt: timeAtX(x, view) - hit.clip.t_start }
    }
    canvasRef.current?.setPointerCapture(e.pointerId)
  }, [localXY, tracks, view, onSelectAudio, canvasRef])

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    const drag = dragRef.current
    if (!drag) return
    const [x] = localXY(e)
    const t = timeAtX(x, view)
    const track = tracks.find((tr) => tr.id === drag.trackId)
    const clip = track?.clips.find((c) => c.id === drag.clipId)
    if (!clip) return
    if (drag.kind === "move") {
      moveAudioClip(drag.trackId, drag.clipId, Math.max(0, t - drag.grabDt))
    } else if (drag.edge === "start") {
      trimAudioClip(drag.trackId, drag.clipId, Math.min(clip.src_end - 0.1, Math.max(0, clip.src_start + (t - clip.t_start))), clip.src_end)
    } else {
      const dur = clip.src_end - clip.src_start
      const newEnd = clip.src_start + Math.max(0.1, (t - clip.t_start))
      trimAudioClip(drag.trackId, drag.clipId, clip.src_start, Math.max(clip.src_start + 0.1, Math.min(clip.src_end + (dur * 4), newEnd)))
    }
  }, [localXY, view, tracks, moveAudioClip, trimAudioClip])

  const onPointerUp = useCallback(() => { dragRef.current = null }, [])

  const onWheel = useCallback((e: React.WheelEvent) => {
    if (!(e.ctrlKey || e.metaKey)) {
      onViewChange((v) => ({ ...v, scrollX: Math.max(0, v.scrollX + e.deltaX + e.deltaY) }))
      return
    }
    const r = canvasRef.current!.getBoundingClientRect()
    const x = e.clientX - r.left
    onViewChange((v) => {
      const focusT = timeAtX(x, v)
      const pxPerSec = Math.max(4, Math.min(400, v.pxPerSec * (e.deltaY < 0 ? 1.25 : 0.8)))
      return { ...v, pxPerSec, scrollX: Math.max(0, focusT * pxPerSec - x) }
    })
  }, [onViewChange, canvasRef])

  return { onPointerDown, onPointerMove, onPointerUp, onWheel }
}
