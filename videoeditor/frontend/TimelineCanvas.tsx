import { useEffect, useRef, useState } from "react"
import type { Clip, VideoMeta } from "./types"
import { fileUrl } from "./api"
import { BANDS, drawTimeline, hitClip, timeAtX, type ViewState } from "./_timelineDraw"

interface Props {
  meta: VideoMeta
  playhead: number
  selectedClipId: string | null
  onSeek: (t: number) => void
  onSelectClip: (id: string | null) => void
  onTrimClip: (id: string, start: number, end: number) => void
}

type Drag =
  | { kind: "scrub" }
  | { kind: "trim"; edge: "start" | "end"; clipId: string }
  | null

export function TimelineCanvas({ meta, playhead, selectedClipId, onSeek, onSelectClip, onTrimClip }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const spriteRef = useRef<HTMLImageElement | null>(null)
  const dragRef = useRef<Drag>(null)
  const [view, setView] = useState<ViewState>({ pxPerSec: 40, scrollX: 0, width: 800 })

  // Sprite-Bild laden
  useEffect(() => {
    if (!meta.sprite_abs) return
    const img = new Image()
    img.onload = () => { spriteRef.current = img; render() }
    img.src = fileUrl(meta.sprite_abs)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta.sprite_abs])

  function render() {
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    drawTimeline({ ctx, v: view, meta, playhead, selectedClipId, sprite: spriteRef.current })
  }

  // Re-Render bei Zustandsänderung
  useEffect(render)

  // Resize-Handling
  useEffect(() => {
    const wrap = wrapRef.current
    const canvas = canvasRef.current
    if (!wrap || !canvas) return
    const measure = () => {
      const w = wrap.clientWidth
      const dpr = window.devicePixelRatio || 1
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(BANDS.height * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${BANDS.height}px`
      setView((v) => ({ ...v, width: w }))
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(wrap)
    return () => ro.disconnect()
  }, [])

  function localXY(e: React.PointerEvent): [number, number] {
    const r = canvasRef.current!.getBoundingClientRect()
    return [e.clientX - r.left, e.clientY - r.top]
  }

  function onPointerDown(e: React.PointerEvent) {
    const [x, y] = localXY(e)
    const hit = hitClip(x, y, meta, view)
    if (hit) {
      onSelectClip(hit.clip.id)
      if (hit.edge) {
        dragRef.current = { kind: "trim", edge: hit.edge, clipId: hit.clip.id }
        canvasRef.current?.setPointerCapture(e.pointerId)
        return
      }
    } else {
      onSelectClip(null)
    }
    onSeek(timeAtX(x, view))
    dragRef.current = { kind: "scrub" }
    canvasRef.current?.setPointerCapture(e.pointerId)
  }

  function onPointerMove(e: React.PointerEvent) {
    const drag = dragRef.current
    if (!drag) return
    const [x] = localXY(e)
    const t = timeAtX(x, view)
    if (drag.kind === "scrub") {
      onSeek(t)
    } else {
      const c = meta.edl?.timeline.find((cl: Clip) => cl.id === drag.clipId)
      if (!c) return
      if (drag.edge === "start") {
        onTrimClip(c.id, Math.min(c.src_end - 0.1, Math.max(0, t)), c.src_end)
      } else {
        onTrimClip(c.id, c.src_start, Math.max(c.src_start + 0.1, Math.min(meta.duration, t)))
      }
    }
  }

  function onPointerUp() { dragRef.current = null }

  function onWheel(e: React.WheelEvent) {
    if (!(e.ctrlKey || e.metaKey)) {
      setView((v) => ({ ...v, scrollX: Math.max(0, v.scrollX + e.deltaX + e.deltaY) }))
      return
    }
    const [x] = localXY(e as unknown as React.PointerEvent)
    setView((v) => {
      const focusT = timeAtX(x, v)
      const pxPerSec = Math.max(4, Math.min(400, v.pxPerSec * (e.deltaY < 0 ? 1.25 : 0.8)))
      return { ...v, pxPerSec, scrollX: Math.max(0, focusT * pxPerSec - x) }
    })
  }

  return (
    <div ref={wrapRef} className="w-full select-none" style={{ background: "#0b0f14" }}>
      <canvas
        ref={canvasRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onWheel={onWheel}
        style={{ display: "block", cursor: "crosshair" }}
      />
    </div>
  )
}
