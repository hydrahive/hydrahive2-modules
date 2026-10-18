/** Bearbeiten der Tonspuren „Sprache“ (A1) und „Musik“ (A2) (Spec „Bauplan Etappe 5“, 5a). Anders als V1 liegen
 *  Tonclips frei: Lücken sind Stille und bleiben stehen. Innerhalb einer Spur überlappen sie nie – ein Clip, der auf
 *  einem anderen landen würde, rückt an die nächste freie Stelle. Reine Funktionen, Zeiten bildgenau auf 1/fps. */
import { MIN_FRAMES } from "./cutEdit"
import type { TimelineClip } from "./timelineApi"

export type AudioTrack = "A1" | "A2"
export const AUDIO_TRACKS: AudioTrack[] = ["A1", "A2"]
export const AUDIO_SECONDS = 10                      // Länge, wenn die Bibliothek sie nicht kennt (der Browser misst nach)

type NewId = () => string
const len = (c: TimelineClip) => c.out - c.in
const end = (c: TimelineClip) => c.start + len(c)
const frame = (t: number, fps: number) => Math.round(t * fps) / fps
const EPS = 1e-6

export function audioTrackFor(kind: string): AudioTrack | null {
  return kind === "music" ? "A2" : kind === "audio" ? "A1" : null
}

export function fromLibraryAudio(item: { kind: string; rel: string; name: string; duration?: number }, start: number, newId: NewId): TimelineClip | null {
  if (!audioTrackFor(item.kind)) return null
  const out = item.duration && item.duration > 0 ? item.duration : AUDIO_SECONDS
  return { id: newId(), kind: "audio", start, in: 0, out, media_rel: item.rel, scene_id: "", shot_id: "", label: item.name }
}

/** Start für einen Clip der Länge `length` möglichst nah an `want`, ohne die anderen zu überlappen. */
export function placeFree(others: TimelineClip[], want: number, length: number, fps: number): number {
  const at = Math.max(0, frame(want, fps))
  const sorted = [...others].sort((x, y) => x.start - y.start)
  const free = (s: number) => s >= -EPS && sorted.every((c) => s + length <= c.start + EPS || s >= end(c) - EPS)
  if (free(at)) return at
  const tries = sorted.flatMap((c) => [frame(end(c), fps), frame(c.start - length, fps)]).filter(free)
  return tries.reduce((best, s) => (Math.abs(s - at) < Math.abs(best - at) ? s : best), tries[0] ?? frame(Math.max(0, ...sorted.map(end)), fps))
}

export function dropAudio(clips: TimelineClip[], clip: TimelineClip, want: number, fps: number): TimelineClip[] {
  return [...clips, { ...clip, start: placeFree(clips, want, len(clip), fps) }]
}

export function moveAudio(clips: TimelineClip[], id: string, want: number, fps: number): TimelineClip[] {
  const c = clips.find((x) => x.id === id)
  if (!c) return clips
  const rest = clips.filter((x) => x.id !== id)
  return [...rest, { ...c, start: placeFree(rest, want, len(c), fps) }]
}

/** Rand um `delta` verschieben. Anfang: Start und Stelle im Medium wandern gemeinsam (der Ton bleibt, wo er war).
 *  Grenzen: Medium-Anfang, bekannte Medienlänge (`durations`), Nachbarn, Mindestlänge. */
export function trimAudio(clips: TimelineClip[], id: string, edge: "start" | "end", delta: number, fps: number,
  durations: Record<string, number> = {}): TimelineClip[] {
  const c = clips.find((x) => x.id === id)
  if (!c) return clips
  const min = MIN_FRAMES / fps
  const others = clips.filter((x) => x.id !== id)
  let next: TimelineClip
  if (edge === "start") {
    const prev = Math.max(0, ...others.filter((x) => end(x) <= c.start + EPS).map(end))
    const d = Math.min(Math.max(delta, -c.in, prev - c.start), len(c) - min)
    next = { ...c, start: frame(c.start + d, fps), in: frame(c.in + d, fps) }
  } else {
    const after = Math.min(Infinity, ...others.filter((x) => x.start >= end(c) - EPS).map((x) => x.start))
    const limit = Math.min(durations[id] ?? Infinity, c.in + (after - c.start))
    next = { ...c, out: frame(Math.max(c.in + min, Math.min(c.out + delta, limit)), fps) }
  }
  return clips.map((x) => (x.id === id ? next : x))
}

/** Teilen am Abspielkopf: liefert beide Hälften oder null (Lücke, zu nah am Rand). */
function cutAudio(clips: TimelineClip[], t: number, fps: number, newId: NewId) {
  const at = frame(t, fps)
  const c = clips.find((x) => at >= x.start && at < end(x))
  if (!c) return null
  const offset = at - c.start
  if (offset * fps < MIN_FRAMES - EPS || (len(c) - offset) * fps < MIN_FRAMES - EPS) return null
  const left = { ...c, out: frame(c.in + offset, fps) }
  const right = { ...c, id: newId(), start: at, in: frame(c.in + offset, fps) }
  return { left, right, rest: clips.filter((x) => x.id !== c.id) }
}

export function splitAudio(clips: TimelineClip[], t: number, fps: number, newId: NewId): TimelineClip[] {
  const r = cutAudio(clips, t, fps, newId)
  return r ? [...r.rest, r.left, r.right] : clips
}

/** Q/W auf einer Tonspur: teilen und den Teil vor („left“) bzw. nach („right“) dem Abspielkopf entfernen. Nichts rückt nach. */
export function splitKeepAudio(clips: TimelineClip[], t: number, drop: "left" | "right", fps: number, newId: NewId): TimelineClip[] {
  const r = cutAudio(clips, t, fps, newId)
  return r ? [...r.rest, drop === "left" ? r.right : r.left] : clips
}

export function duplicateAudio(clips: TimelineClip[], id: string, fps: number, newId: NewId): TimelineClip[] {
  const c = clips.find((x) => x.id === id)
  return c ? dropAudio(clips, { ...c, id: newId() }, end(c), fps) : clips
}

/** Hörbarer Tonclip bei t; gelöschte Medien sind still. */
export function audioAt(clips: TimelineClip[], t: number): TimelineClip | null {
  return clips.find((c) => !c.missing && c.media_rel && t >= c.start && t < end(c)) ?? null
}

