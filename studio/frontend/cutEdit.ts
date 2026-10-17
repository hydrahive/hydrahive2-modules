/** Bearbeiten der Hauptspur (Spec „Bauplan 4b“): magnetisch – Clips liegen immer lückenlos hintereinander.
 *  Reine Funktionen: neue Liste zurück, Eingabe bleibt unverändert. Zeiten bildgenau auf 1/fps. */
import type { TimelineClip } from "./timelineApi"

export const MIN_FRAMES = 5
export const IMAGE_SECONDS = 5
const SNAP_PX = 8

type NewId = () => string
const len = (c: TimelineClip) => c.out - c.in
const frame = (t: number, fps: number) => Math.round(t * fps) / fps
const byStart = (cs: TimelineClip[]) => [...cs].sort((a, b) => a.start - b.start)

/** Lückenlos ab 0 in der bisherigen Reihenfolge; Zeiten bildgenau. */
export function pack(clips: TimelineClip[], fps: number): TimelineClip[] {
  let t = 0
  return byStart(clips).map((c) => {
    const tin = frame(c.in, fps)
    const out = Math.max(frame(c.out, fps), tin + MIN_FRAMES / fps)
    const next = { ...c, start: frame(t, fps), in: tin, out }
    t += out - tin
    return next
  })
}

/** Stelle in der Liste (0 … n), an der ein bei Zeit t abgelegter Clip landet: vor/hinter der Mitte eines Clips. */
export function insertAt(clips: TimelineClip[], t: number): number {
  const sorted = byStart(clips)
  const i = sorted.findIndex((c) => t < c.start + len(c) / 2)
  return i < 0 ? sorted.length : i
}

/** Clip an die Stelle `index` der Liste ohne ihn setzen. */
export function moveTo(clips: TimelineClip[], id: string, index: number, fps: number): TimelineClip[] {
  const sorted = byStart(clips)
  const from = sorted.findIndex((c) => c.id === id)
  if (from < 0) return clips
  const rest = sorted.filter((c) => c.id !== id)
  const to = Math.max(0, Math.min(index, rest.length))
  if (to === from) return clips
  rest.splice(to, 0, sorted[from])
  return pack(rest.map((c, i) => ({ ...c, start: i })), fps)
}

/** Teilen am Abspielkopf. Liefert die neue Liste und die beiden Hälften (oder null, wenn nichts zu teilen ist). */
function cut(clips: TimelineClip[], t: number, fps: number, newId: NewId) {
  const at = frame(t, fps)
  const c = clips.find((x) => at > x.start && at < x.start + len(x))
  if (!c) return null
  const offset = at - c.start
  if (offset * fps < MIN_FRAMES - 1e-6 || (len(c) - offset) * fps < MIN_FRAMES - 1e-6) return null
  const left = { ...c, out: frame(c.in + offset, fps) }
  const right = { ...c, id: newId(), start: at, in: frame(c.in + offset, fps) }
  return { left, right, list: pack(clips.flatMap((x) => (x.id === c.id ? [left, right] : [x])), fps) }
}

export function splitAt(clips: TimelineClip[], t: number, fps: number, newId: NewId): TimelineClip[] {
  return cut(clips, t, fps, newId)?.list ?? clips
}

/** Q/W: teilen und den Teil vor („left“) bzw. nach („right“) dem Abspielkopf entfernen. */
export function splitKeep(clips: TimelineClip[], t: number, drop: "left" | "right", fps: number, newId: NewId): TimelineClip[] {
  const r = cut(clips, t, fps, newId)
  if (!r) return clips
  const gone = drop === "left" ? r.left.id : r.right.id
  return pack(r.list.filter((x) => x.id !== gone), fps)
}

/** Rand eines Clips um `delta` Sekunden verschieben. `durations` = bekannte Länge der Videos (Clip-ID → Sekunden). */
export function trim(clips: TimelineClip[], id: string, edge: "start" | "end", delta: number, fps: number,
  durations: Record<string, number> = {}): TimelineClip[] {
  const min = MIN_FRAMES / fps
  return pack(clips.map((c) => {
    if (c.id !== id) return c
    if (edge === "start") return { ...c, in: frame(Math.min(Math.max(0, c.in + delta), c.out - min), fps) }
    const limit = c.kind === "video" && durations[c.id] ? durations[c.id] : Infinity
    return { ...c, out: frame(Math.max(Math.min(c.out + delta, limit), c.in + min), fps) }
  }), fps)
}

export function remove(clips: TimelineClip[], id: string, fps: number): TimelineClip[] {
  return pack(clips.filter((c) => c.id !== id), fps)
}

/** Clip an Stelle `index` einfügen (Rest rückt nach). */
export function append(clips: TimelineClip[], clip: TimelineClip, index: number, fps: number): TimelineClip[] {
  const sorted = byStart(clips)
  sorted.splice(Math.max(0, Math.min(index, sorted.length)), 0, clip)
  return pack(sorted.map((c, i) => ({ ...c, start: i })), fps)
}

/** Kopie hinter `afterId` einfügen (ohne `afterId`: ans Ende). */
export function paste(clips: TimelineClip[], clip: TimelineClip, afterId: string | null, fps: number, newId: NewId): TimelineClip[] {
  const sorted = byStart(clips)
  const i = afterId ? sorted.findIndex((c) => c.id === afterId) : -1
  const { missing: _m, ...rest } = clip
  return append(sorted, { ...rest, ...(clip.missing ? { missing: true } : {}), id: newId() }, i < 0 ? sorted.length : i + 1, fps)
}

export function duplicate(clips: TimelineClip[], id: string, fps: number, newId: NewId): TimelineClip[] {
  const c = clips.find((x) => x.id === id)
  return c ? paste(clips, c, id, fps, newId) : clips
}

/** Clip aus einem Bibliothekseintrag; Musik, Sprache und Figuren gehen (noch) nicht → null. */
export function fromLibrary(item: { kind: string; rel: string; name: string; duration?: number }, newId: NewId): TimelineClip | null {
  if (item.kind !== "image" && item.kind !== "video") return null
  const out = item.kind === "video" && item.duration && item.duration > 0 ? item.duration : IMAGE_SECONDS
  return { id: newId(), kind: item.kind, start: 0, in: 0, out, media_rel: item.rel, scene_id: "", shot_id: "", label: item.name }
}

/** Rand an einem der Ziele (z. B. Abspielkopf) einrasten lassen, wenn er auf dem Bildschirm nah genug ist. */
export function snapEdge(t: number, targets: number[], span: number, widthPx: number): number {
  const px = widthPx > 0 ? span / widthPx : 0
  const hit = targets.find((x) => Math.abs(x - t) <= SNAP_PX * px)
  return hit ?? t
}
