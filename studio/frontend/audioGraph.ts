/** Web Audio für die Vorschau (Spec „Bauplan 5b“): jedes Medium-Element bekommt eine Verstärkung (auch über 0 dB), jeder
 *  Kanal (Originalton, Sprache, Musik) einen Analyser für die Pegelanzeige. Ein Element kann nur einmal an Web Audio
 *  hängen – daher ein Speicher je Element. Ohne Web Audio (alter Browser, Fehler) bleibt `element.volume` (max. 0 dB). */
import type { TrackId } from "./timelineApi"

type Chain = { gain: GainNode } | { fallback: HTMLMediaElement }
let ctx: AudioContext | null = null
let broken = false
const chains = new WeakMap<HTMLMediaElement, Chain>()
const meters = new Map<TrackId, AnalyserNode>()

function context(): AudioContext | null {
  if (broken) return null
  try {
    if (!ctx) {
      const C = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (!C) { broken = true; return null }
      ctx = new C()
    }
    if (ctx.state === "suspended") void ctx.resume().catch(() => {})
    return ctx
  } catch { broken = true; return null }
}

function meter(c: AudioContext, track: TrackId): AnalyserNode {
  let m = meters.get(track)
  if (!m) {
    m = c.createAnalyser()
    m.fftSize = 512
    m.connect(c.destination)
    meters.set(track, m)
  }
  return m
}

/** Lautstärke-Faktor (linear, auch > 1) für ein Medium-Element auf einem Kanal setzen. */
export function setGain(el: HTMLMediaElement | null, track: TrackId, factor: number): void {
  if (!el) return
  let ch = chains.get(el)
  if (!ch) {
    const c = context()
    try {
      if (!c) throw new Error("kein Web Audio")
      const src = c.createMediaElementSource(el)
      const gain = c.createGain()
      src.connect(gain).connect(meter(c, track))
      ch = { gain }
    } catch { ch = { fallback: el } }
    chains.set(el, ch)
  }
  const f = Number.isFinite(factor) ? Math.max(0, factor) : 0
  if ("gain" in ch) ch.gain.gain.value = f
  else el.volume = Math.min(1, f)
}

/** Aktueller Spitzenpegel eines Kanals in dB (−Infinity = still, ohne Web Audio null). */
export function peakDb(track: TrackId): number | null {
  const m = meters.get(track)
  if (!m) return null
  const buf = new Float32Array(m.fftSize)
  m.getFloatTimeDomainData(buf)
  let peak = 0
  for (const v of buf) peak = Math.max(peak, Math.abs(v))
  return peak > 0 ? 20 * Math.log10(peak) : -Infinity
}

/** Für Tests: alles zurücksetzen. */
export function resetAudioGraph(): void { ctx = null; broken = false; meters.clear() }
