// Reines Canvas-Zeichen-Modul für die Timeline — keine React-Abhängigkeit,
// damit die Komponente schlank bleibt. Eigene Implementierung (kein Fremdcode).
import type { Clip, SpriteMeta, VideoMeta } from "./types"

export interface Bands {
  RULER_H: number
  KF_H: number
  FILM_H: number
  CLIP_H: number
  GAP: number
  filmY: number
  clipY: number
  height: number
}

export const BANDS: Bands = (() => {
  const RULER_H = 22, KF_H = 10, FILM_H = 46, CLIP_H = 40, GAP = 4
  const filmY = RULER_H + GAP + KF_H + GAP
  const clipY = filmY + FILM_H + GAP
  return { RULER_H, KF_H, FILM_H, CLIP_H, GAP, filmY, clipY, height: clipY + CLIP_H + GAP }
})()

export interface ViewState {
  pxPerSec: number
  scrollX: number
  width: number
}

export const xAtTime = (t: number, v: ViewState) => t * v.pxPerSec - v.scrollX
export const timeAtX = (x: number, v: ViewState) => Math.max(0, (x + v.scrollX) / v.pxPerSec)

function pickTickStep(pxPerSec: number): number {
  const targetSec = 80 / pxPerSec
  for (const s of [0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600]) {
    if (s >= targetSec) return s
  }
  return 1200
}

function fmtTime(t: number, pxPerSec: number): string {
  if (t < 0) t = 0
  const m = Math.floor(t / 60)
  const s = t - m * 60
  return pxPerSec >= 60
    ? `${m}:${s.toFixed(1).padStart(4, "0")}`
    : `${m}:${String(Math.floor(s)).padStart(2, "0")}`
}

interface DrawCtx {
  ctx: CanvasRenderingContext2D
  v: ViewState
  meta: VideoMeta
  playhead: number
  selectedClipId: string | null
  playingClipId?: string | null
  sprite: HTMLImageElement | null
}

export function drawTimeline(d: DrawCtx): void {
  const { ctx, v } = d
  ctx.clearRect(0, 0, v.width, BANDS.height)
  ctx.fillStyle = "#0b0f14"
  ctx.fillRect(0, 0, v.width, BANDS.height)
  drawRuler(d)
  drawKeyframes(d)
  drawFilmstrip(d)
  drawClips(d)
  drawPlayhead(d)
}

function drawRuler(d: DrawCtx): void {
  const { ctx, v } = d
  ctx.fillStyle = "#161f2b"
  ctx.fillRect(0, 0, v.width, BANDS.RULER_H)
  const step = pickTickStep(v.pxPerSec)
  ctx.fillStyle = "#64748b"
  ctx.font = '11px ui-monospace, monospace'
  const tStart = Math.floor(v.scrollX / v.pxPerSec / step) * step
  const tEnd = v.scrollX / v.pxPerSec + v.width / v.pxPerSec
  for (let t = tStart; t <= tEnd; t += step) {
    const x = xAtTime(t, v)
    if (x < -20 || x > v.width + 20) continue
    ctx.strokeStyle = "#26344a"
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, BANDS.RULER_H); ctx.stroke()
    ctx.fillText(fmtTime(t, v.pxPerSec), x + 3, 14)
  }
}

function drawKeyframes(d: DrawCtx): void {
  const { ctx, v, meta } = d
  const y = BANDS.RULER_H + BANDS.GAP
  ctx.fillStyle = "#0f1924"
  ctx.fillRect(0, y, v.width, BANDS.KF_H)
  ctx.fillStyle = "#d4a373"
  for (const kf of meta.keyframes) {
    const x = xAtTime(kf, v)
    if (x < -2 || x > v.width + 2) continue
    ctx.fillRect(x - 0.5, y + 1, 1, BANDS.KF_H - 2)
  }
}

function drawFilmstrip(d: DrawCtx): void {
  const { ctx, v, meta, sprite } = d
  ctx.fillStyle = "#07101a"
  ctx.fillRect(0, BANDS.filmY, v.width, BANDS.FILM_H)
  const sm = meta.sprite
  if (!sm || !sprite) return
  const destW = Math.max(1, Math.round(BANDS.FILM_H * (sm.tile_w / sm.tile_h)))
  const tilePx = v.pxPerSec * sm.interval
  const stride = Math.max(1, Math.ceil(destW / Math.max(1, tilePx * 0.98)))
  const iStart = Math.max(0, Math.floor(v.scrollX / v.pxPerSec / sm.interval))
  const iEnd = Math.min(sm.count - 1, Math.ceil((v.scrollX + v.width) / v.pxPerSec / sm.interval))
  const iFirst = iStart - (iStart % stride)
  for (let i = iFirst; i <= iEnd; i += stride) {
    if (i < 0) continue
    const x = xAtTime(i * sm.interval, v)
    const col = i % sm.cols, row = Math.floor(i / sm.cols)
    ctx.drawImage(sprite, col * sm.tile_w, row * sm.tile_h, sm.tile_w, sm.tile_h,
      x, BANDS.filmY, destW, BANDS.FILM_H)
  }
}

function drawClips(d: DrawCtx): void {
  const { ctx, v, meta, selectedClipId, playingClipId } = d
  for (const c of meta.edl?.timeline ?? []) {
    const x0 = xAtTime(c.src_start, v)
    const w = Math.max(2, xAtTime(c.src_end, v) - x0)
    ctx.fillStyle = c.mode === "copy" ? "#0d9488" : "#6366f1"
    ctx.fillRect(x0, BANDS.clipY, w, BANDS.CLIP_H)
    if (playingClipId === c.id) {
      ctx.fillStyle = "rgba(234,179,8,0.30)"
      ctx.fillRect(x0, BANDS.clipY, w, BANDS.CLIP_H)
    }
    const active = playingClipId === c.id
    ctx.strokeStyle = active ? "#eab308" : (selectedClipId === c.id ? "#38bdf8" : "rgba(255,255,255,0.15)")
    ctx.lineWidth = (active || selectedClipId === c.id) ? 2 : 1
    ctx.strokeRect(x0 + 0.5, BANDS.clipY + 0.5, w - 1, BANDS.CLIP_H - 1)
    ctx.fillStyle = "rgba(255,255,255,0.3)"
    ctx.fillRect(x0, BANDS.clipY, 3, BANDS.CLIP_H)
    ctx.fillRect(x0 + w - 3, BANDS.clipY, 3, BANDS.CLIP_H)
    ctx.fillStyle = "#e5eaf0"
    ctx.font = '11px ui-monospace, monospace'
    ctx.save(); ctx.beginPath(); ctx.rect(x0 + 4, BANDS.clipY, w - 8, BANDS.CLIP_H); ctx.clip()
    ctx.fillText(`${c.mode} · ${(c.src_end - c.src_start).toFixed(2)}s`, x0 + 6, BANDS.clipY + 24)
    ctx.restore()
  }
}

function drawPlayhead(d: DrawCtx): void {
  const { ctx, v, meta, playhead } = d
  const tol = 1 / (meta.fps || 25)
  const onKf = meta.keyframes.some((k) => Math.abs(k - playhead) <= tol)
  const color = onKf ? "#22c55e" : "#f472b6"
  const px = xAtTime(playhead, v)
  ctx.strokeStyle = color
  ctx.lineWidth = 2
  ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, BANDS.height); ctx.stroke()
  ctx.fillStyle = color
  ctx.beginPath(); ctx.moveTo(px - 5, 0); ctx.lineTo(px + 5, 0); ctx.lineTo(px, 8); ctx.closePath(); ctx.fill()
}

/** Hit-Test: welcher Clip / welche Kante liegt an Position (x,y)? */
export function hitClip(x: number, y: number, meta: VideoMeta, v: ViewState): { clip: Clip; edge: "start" | "end" | null } | null {
  if (y < BANDS.clipY || y > BANDS.clipY + BANDS.CLIP_H) return null
  for (const c of meta.edl?.timeline ?? []) {
    const x0 = xAtTime(c.src_start, v)
    const x1 = xAtTime(c.src_end, v)
    if (x >= x0 && x <= x1) {
      const edge = x - x0 < 6 ? "start" : x1 - x < 6 ? "end" : null
      return { clip: c, edge }
    }
  }
  return null
}

export type { SpriteMeta }
