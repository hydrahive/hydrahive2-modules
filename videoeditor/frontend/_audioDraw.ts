// Reines Canvas-Zeichen-Modul für Audiospuren + Wellenform — keine React-Abhängigkeit.
// Zeitachse ist an _timelineDraw gekoppelt (gleicher ViewState + xAtTime/timeAtX),
// damit Audio- und Video-Timeline pixelgenau synchron laufen. Eigene Implementierung.
import { xAtTime, type ViewState } from "./_timelineDraw"
import type { AudioTrack, AudioClip, AudioPeaks } from "./types"

export const AUDIO_ROW_H = 56       // Höhe einer Spur-Zeile im Clip-Bereich
export const AUDIO_CLIP_PAD = 2

// Audio-Clips heben sich farblich vom Video-Band ab (Grün-/Cyan-Töne).
const CLIP_FILL = "#0d9488"
const CLIP_FILL_MUTE = "#134e4a"
const WAVE_COLOR = "#5eead4"
const SEL_COLOR = "#38bdf8"
const ROW_BG = "#07101a"
const ROW_BG_ALT = "#0f1924"

/** Dauer eines Audio-Clips auf der Timeline = sichtbarer Quell-Ausschnitt. */
const clipDur = (c: AudioClip) => Math.max(0, c.src_end - c.src_start)

interface AudioDrawCtx {
  ctx: CanvasRenderingContext2D
  v: ViewState
  y: number                     // oberer Rand dieser Spur-Zeile
  track: AudioTrack
  peaksByClipId: Record<string, AudioPeaks | undefined>
  selectedClipId: string | null
  playhead?: number
}

/** Zeichnet EINE Audiospur-Zeile. Aufrufer ruft pro Spur mit passendem y auf. */
export function drawAudioTrack(d: AudioDrawCtx): void {
  const { ctx, v, y, track, peaksByClipId, selectedClipId } = d

  // Zeilen-Hintergrund
  ctx.fillStyle = track.mute ? ROW_BG_ALT : ROW_BG
  ctx.fillRect(0, y, v.width, AUDIO_ROW_H)
  ctx.strokeStyle = "rgba(255,255,255,0.06)"
  ctx.beginPath(); ctx.moveTo(0, y + AUDIO_ROW_H - 0.5); ctx.lineTo(v.width, y + AUDIO_ROW_H - 0.5); ctx.stroke()

  const boxY = y + AUDIO_CLIP_PAD
  const boxH = AUDIO_ROW_H - AUDIO_CLIP_PAD * 2
  const mid = boxY + boxH / 2

  for (const c of track.clips) {
    const x0 = xAtTime(c.t_start, v)
    const w = Math.max(2, xAtTime(c.t_start + clipDur(c), v) - x0)
    if (x0 > v.width || x0 + w < 0) continue

    // Clip-Box
    ctx.fillStyle = track.mute ? CLIP_FILL_MUTE : CLIP_FILL
    ctx.fillRect(x0, boxY, w, boxH)

    const peaks = peaksByClipId[c.id]
    if (peaks) {
      drawWave(ctx, v, c, peaks, x0, w, boxY, boxH, mid)
    } else {
      // Platzhalter bis Peaks geladen sind
      ctx.strokeStyle = "rgba(255,255,255,0.25)"
      ctx.lineWidth = 1
      ctx.beginPath(); ctx.moveTo(x0 + 1, mid + 0.5); ctx.lineTo(x0 + w - 1, mid + 0.5); ctx.stroke()
    }

    // Fade-Andeutung (nice-to-have)
    if (c.fade_in > 0 || c.fade_out > 0) {
      ctx.strokeStyle = "rgba(255,255,255,0.35)"
      ctx.lineWidth = 1
      if (c.fade_in > 0) {
        const fw = Math.min(w, c.fade_in * v.pxPerSec)
        ctx.beginPath(); ctx.moveTo(x0, boxY + boxH); ctx.lineTo(x0 + fw, boxY); ctx.stroke()
      }
      if (c.fade_out > 0) {
        const fw = Math.min(w, c.fade_out * v.pxPerSec)
        ctx.beginPath(); ctx.moveTo(x0 + w - fw, boxY); ctx.lineTo(x0 + w, boxY + boxH); ctx.stroke()
      }
    }

    // Kanten-Griffe
    ctx.fillStyle = "rgba(255,255,255,0.3)"
    ctx.fillRect(x0, boxY, 3, boxH)
    ctx.fillRect(x0 + w - 3, boxY, 3, boxH)

    // Auswahl-Rahmen (wie drawClips)
    ctx.strokeStyle = selectedClipId === c.id ? SEL_COLOR : "rgba(255,255,255,0.15)"
    ctx.lineWidth = selectedClipId === c.id ? 2 : 1
    ctx.strokeRect(x0 + 0.5, boxY + 0.5, w - 1, boxH - 1)
  }
}

/**
 * Zeichnet die normalisierte Wellenform in die Clip-Box.
 * Nur der sichtbare Ausschnitt src_start..src_end wird gezeigt: Peak-Index i wird
 * über peaks_per_second auf die Quellzeit t_src abgebildet; sichtbar wenn
 * src_start ≤ t_src ≤ src_end. Timeline-x = xAtTime(t_start + (t_src - src_start)).
 */
function drawWave(
  ctx: CanvasRenderingContext2D, v: ViewState, c: AudioClip, peaks: AudioPeaks,
  x0: number, w: number, boxY: number, boxH: number, mid: number,
): void {
  const pps = peaks.peaks_per_second
  if (!pps || peaks.max.length === 0) return
  const half = boxH / 2 - 1

  const iStart = Math.max(0, Math.floor(c.src_start * pps))
  const iEnd = Math.min(peaks.max.length - 1, Math.ceil(c.src_end * pps))

  ctx.save()
  ctx.beginPath(); ctx.rect(x0, boxY, w, boxH); ctx.clip()
  ctx.fillStyle = WAVE_COLOR
  for (let i = iStart; i <= iEnd; i++) {
    const tSrc = i / pps
    if (tSrc < c.src_start || tSrc > c.src_end) continue
    const x = xAtTime(c.t_start + (tSrc - c.src_start), v)
    if (x < x0 - 1 || x > x0 + w + 1) continue
    const mx = Math.max(0, Math.min(1, peaks.max[i] ?? 0))
    const mn = Math.max(-1, Math.min(0, peaks.min[i] ?? 0))
    const top = mid - mx * half
    const bot = mid - mn * half
    ctx.fillRect(x, top, 1, Math.max(1, bot - top))
  }
  ctx.restore()
}

/**
 * Hit-Test über alle Audiospuren: bestimmt aus y die Spur-Zeile (Index über
 * AUDIO_ROW_H ab firstRowY) und aus x den getroffenen Clip / die Kante (Toleranz 6px).
 */
export function hitAudioClip(
  x: number, y: number, tracks: AudioTrack[], v: ViewState, firstRowY: number,
): { trackId: string; clip: AudioClip; edge: "start" | "end" | null } | null {
  if (y < firstRowY) return null
  const row = Math.floor((y - firstRowY) / AUDIO_ROW_H)
  if (row < 0 || row >= tracks.length) return null
  const track = tracks[row]
  for (const c of track.clips) {
    const x0 = xAtTime(c.t_start, v)
    const x1 = xAtTime(c.t_start + clipDur(c), v)
    if (x >= x0 && x <= x1) {
      const edge = x - x0 < 6 ? "start" : x1 - x < 6 ? "end" : null
      return { trackId: track.id, clip: c, edge }
    }
  }
  return null
}
