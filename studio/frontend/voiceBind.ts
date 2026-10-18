/** Sprache gehört zum Shot (Spec „Bauplan 5c“): Ein Sprachclip mit `shot_id` beginnt immer am Anfang des (ersten)
 *  Bildclips desselben Shots, ist höchstens so lang wie dieser und verschwindet mit ihm. Freie Sprachclips (ohne
 *  `shot_id`) bleiben stehen; liegen sie im Weg, rücken sie an die nächste freie Stelle. Rein, damit testbar. */
import { placeFree } from "./cutAudio"
import type { Tracks } from "./cutTracks"
import type { TimelineClip } from "./timelineApi"

const len = (c: TimelineClip) => c.out - c.in

/** Spuren nach einer Änderung auf V1 (`before` → `after`) nachziehen. Unverändert → `after` selbst. */
export function followPictures(before: Tracks, after: Tracks, fps: number): Tracks {
  if (before.V1 === after.V1 && before.A1 === after.A1) return after
  const first = new Map<string, TimelineClip>()
  for (const p of [...after.V1].sort((a, b) => a.start - b.start)) if (p.shot_id && !first.has(p.shot_id)) first.set(p.shot_id, p)
  const bound: TimelineClip[] = []
  for (const s of after.A1) {
    if (!s.shot_id) continue
    const pic = first.get(s.shot_id)
    if (!pic) continue                                                   // Bildclip weg → Sprache weg
    const out = Math.min(s.out, s.in + len(pic))                       // nur kappen – Ton muss nicht bildgenau enden
    bound.push(s.start === pic.start && out === s.out ? s : { ...s, start: pic.start, out })
  }
  let placed = [...bound]
  for (const f of after.A1.filter((s) => !s.shot_id)) placed = [...placed, { ...f, start: placeFree(placed, f.start, len(f), fps) }]
  const same = placed.length === after.A1.length && placed.every((x) => after.A1.some((y) => y.id === x.id && y.start === x.start && y.out === x.out))
  return same ? after : { ...after, A1: placed.map((x) => after.A1.find((y) => y.id === x.id && y.start === x.start && y.out === x.out) ?? x) }
}

/** „Vom Shot lösen“: Sprachclip bleibt, wandert aber nicht mehr mit. */
export function unbind(tr: Tracks, clipId: string): Tracks {
  if (!tr.A1.some((c) => c.id === clipId && c.shot_id)) return tr
  return { ...tr, A1: tr.A1.map((c) => (c.id === clipId ? { ...c, shot_id: "" } : c)) }
}
