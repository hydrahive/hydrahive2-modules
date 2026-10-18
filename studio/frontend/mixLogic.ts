/** Mischpult (Spec „Bauplan 5b“): reine Rechenhilfen für Vorschau und Bedienung. Die Ducking-Kurve ist dieselbe wie auf
 *  dem Server (backend/mix.py) – geprüft über eine gemeinsame Tabelle (duckTable.test.json). */
import type { Timeline, TimelineClip, TrackId, TrackMix } from "./timelineApi"

export const GAIN_MIN = -60
export const GAIN_MAX = 12
export const DUCK_DB = -12
const RAMP_DOWN = 0.2
const RAMP_UP = 0.6
const MERGE_GAP = 0.8
const MAX_SPANS = 300

export type Span = [number, number]
export interface Mixer { tracks: Record<TrackId, TrackMix>; duck: boolean }

export const fromDb = (db: number): number => 10 ** (db / 20)
export const toDb = (f: number): number => (f > 0 ? 20 * Math.log10(f) : -Infinity)
const clampGain = (v: number) => Math.round(Math.min(GAIN_MAX, Math.max(GAIN_MIN, v)) * 10) / 10

export function mixerOf(tl: Timeline | null): Mixer {
  const pick = (id: TrackId): TrackMix => {
    const t = tl?.tracks.find((x) => x.id === id)
    const out: TrackMix = {}
    if (t?.gain_db) out.gain_db = t.gain_db
    if (t?.mute) out.mute = true
    if (t?.solo) out.solo = true
    return out
  }
  return { tracks: { V1: pick("V1"), A1: pick("A1"), A2: pick("A2") }, duck: tl?.duck !== false }
}

/** Spuren, die klingen: mit Solo nur die Solo-Spuren (Solo schlägt Stumm), sonst alle nicht stummen. */
export function audibleTracks(tracks: Record<string, TrackMix>): Set<string> {
  const solo = Object.keys(tracks).filter((k) => tracks[k].solo)
  return new Set(solo.length ? solo : Object.keys(tracks).filter((k) => !tracks[k].mute))
}

export function duckSpans(spans: Span[]): Span[] {
  let gap = MERGE_GAP
  for (;;) {
    const out: Span[] = []
    for (const [a, b] of [...spans].sort((x, y) => x[0] - y[0] || x[1] - y[1])) {
      const last = out[out.length - 1]
      if (last && a - last[1] < gap) last[1] = Math.max(last[1], b)
      else out.push([a, b])
    }
    if (out.length <= MAX_SPANS) return out
    gap *= 2
  }
}

function spanDb(t: number, a: number, b: number): number {
  if (t < a - RAMP_DOWN || t > b + RAMP_UP) return 0
  if (t < a) return (DUCK_DB * (t - (a - RAMP_DOWN))) / RAMP_DOWN
  if (t <= b) return DUCK_DB
  return DUCK_DB * (1 - (t - b) / RAMP_UP)
}

export function duckFactor(spans: Span[], t: number): number {
  return fromDb(spans.reduce((m, [a, b]) => Math.min(m, spanDb(t, a, b)), 0))
}

/** Ein-/Ausblenden bei Filmzeit t (linear in der Lautstärke, wie ffmpeg afade). */
export function fadeFactor(c: TimelineClip, t: number): number {
  const pos = t - c.start
  const len = c.out - c.in
  let f = 1
  if (c.fade_in && pos < c.fade_in) f = Math.min(f, Math.max(0, pos / c.fade_in))
  if (c.fade_out && pos > len - c.fade_out) f = Math.min(f, Math.max(0, (len - pos) / c.fade_out))
  return f
}

/** Lautstärke-Faktor eines Tonclips bei t: hörbar? × Clip × Spur × Blende × Ducking (nur Musik). `voice` = Sprachzeiträume. */
export function clipGain(mx: Mixer, track: TrackId, c: TimelineClip, t: number, voice: Span[]): number {
  if (!audibleTracks(mx.tracks).has(track)) return 0
  let f = fromDb((c.gain_db ?? 0) + (mx.tracks[track].gain_db ?? 0)) * fadeFactor(c, t)
  if (track === "A2" && mx.duck && voice.length) f *= duckFactor(voice, t)
  return f
}

/** Sprachzeiträume für das Ducking (nur wenn „Sprache“ klingt). */
export function voiceSpans(mx: Mixer, voiceClips: TimelineClip[]): Span[] {
  if (!mx.duck || !audibleTracks(mx.tracks).has("A1")) return []
  return duckSpans(voiceClips.filter((c) => !c.missing && c.media_rel).map((c) => [c.start, c.start + c.out - c.in]))
}

export function setTrackMix(tl: Timeline, id: TrackId, v: TrackMix): Timeline {
  return { ...tl, tracks: tl.tracks.map((t) => {
    if (t.id !== id) return t
    const next = { ...t, ...v }
    if (v.gain_db !== undefined) next.gain_db = clampGain(v.gain_db)
    if (!next.gain_db) delete next.gain_db
    if (!next.mute) delete next.mute
    if (!next.solo) delete next.solo
    return next
  }) }
}

export function setClipMix(tl: Timeline, clipId: string, v: { gain_db?: number; fade_in?: number; fade_out?: number }): Timeline {
  if (!tl.tracks.some((t) => t.clips.some((c) => c.id === clipId))) return tl
  return { ...tl, tracks: tl.tracks.map((t) => ({ ...t, clips: t.clips.map((c) => {
    if (c.id !== clipId) return c
    const len = c.out - c.in
    const next = { ...c, ...v }
    if (v.gain_db !== undefined) next.gain_db = clampGain(v.gain_db)
    const r = (n: number) => Math.round(n * 100) / 100
    if (v.fade_in !== undefined) next.fade_in = r(Math.min(Math.max(0, v.fade_in), len - (next.fade_out ?? 0)))
    if (v.fade_out !== undefined) next.fade_out = r(Math.min(Math.max(0, v.fade_out), len - (next.fade_in ?? 0)))
    for (const k of ["gain_db", "fade_in", "fade_out"] as const) if (!next[k]) delete next[k]
    return next
  }) })) }
}

export const setDuck = (tl: Timeline, on: boolean): Timeline => ({ ...tl, duck: on })

/** Lautstärke-Faktor des Originaltons (Kanal „Originalton“ = Spur V1); 0 = stumm bzw. nicht im Solo. */
export const originalGain = (mx: Mixer): number => (audibleTracks(mx.tracks).has("V1") ? fromDb(mx.tracks.V1.gain_db ?? 0) : 0)

/** Zahl der Clips je Spur (Anzeige im Mischpult). */
export function countsOf(tl: Timeline | null): Record<TrackId, number> {
  const n = (id: TrackId) => tl?.tracks.find((t) => t.id === id)?.clips.length ?? 0
  return { V1: n("V1"), A1: n("A1"), A2: n("A2") }
}

/** −3.5 → „−3,5 dB“, 2 → „+2,0 dB“ */
export const dbText = (db: number): string => `${db > 0 ? "+" : db < 0 ? "−" : ""}${Math.abs(db).toFixed(1).replace(".", ",")} dB`
