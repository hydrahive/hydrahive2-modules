import type { Clip } from "./types"

/** Pure Transformationen auf der Video-Clip-Timeline (Clip[]). Keine React-/
 *  Save-Logik — der Hook (useEditorEdl) wickelt History + Auto-Save darum,
 *  symmetrisch zu _audioEdlOps.ts. */

export function uid(): string {
  return "c" + Math.random().toString(36).slice(2, 10)
}

/** Neuen Bereich anlegen. Beide Kanten auf Keyframe → verlustfrei kopierbar. */
export function addRange(
  clips: Clip[], s: number, e: number, onKeyframe: (t: number) => boolean,
): { clips: Clip[]; id: string } | null {
  if (e - s < 0.1) return null
  const mode: Clip["mode"] = onKeyframe(s) && onKeyframe(e) ? "copy" : "reencode"
  const clip: Clip = { id: uid(), src_start: Number(s.toFixed(3)), src_end: Number(e.toFixed(3)), mode }
  return { clips: [...clips, clip].sort((a, b) => a.src_start - b.src_start), id: clip.id }
}

export function splitAt(clips: Clip[], cut: number): { clips: Clip[]; id: string } | null {
  const target = clips.find((c) => cut > c.src_start + 0.01 && cut < c.src_end - 0.01)
  if (!target) return null
  const right: Clip = { id: uid(), src_start: cut, src_end: target.src_end, mode: target.mode }
  const next = clips.flatMap((c) => (c.id !== target.id ? [c] : [{ ...c, src_end: cut }, right]))
  return { clips: next, id: right.id }
}

export function trim(clips: Clip[], id: string, start: number, end: number): Clip[] {
  return clips
    .map((c) => (c.id === id
      ? { ...c, src_start: Math.max(0, Math.min(start, end)), src_end: Math.max(start, end) }
      : c))
    .sort((a, b) => a.src_start - b.src_start)
}

export function remove(clips: Clip[], id: string): Clip[] {
  return clips.filter((c) => c.id !== id)
}

export function toggleMode(clips: Clip[], id: string): Clip[] {
  return clips.map((c) => (c.id === id
    ? { ...c, mode: c.mode === "copy" ? "reencode" : "copy" as Clip["mode"] }
    : c))
}
