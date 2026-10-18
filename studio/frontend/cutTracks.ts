/** Bearbeiten über alle Spuren (Spec „Bauplan Etappe 5“, 5a): leitet jede Bearbeitung an die Spur des gewählten Clips
 *  weiter – V1 magnetisch (cutEdit), Tonspuren frei (cutAudio). Ohne Auswahl wirkt Teilen auf V1. Rein, damit testbar. */
import {
  AUDIO_TRACKS, audioTrackFor, dropAudio, duplicateAudio, fromLibraryAudio, moveAudio, splitAudio, splitKeepAudio, trimAudio,
  type AudioTrack,
} from "./cutAudio"
import { append, duplicate, fromLibrary, moveTo, paste, remove, splitAt, splitKeep, trim } from "./cutEdit"
import type { EditAction } from "./cutKeys"
import { clipsOf, withTrack, type Timeline, type TimelineClip, type TrackId } from "./timelineApi"

export type Tracks = Record<TrackId, TimelineClip[]>
type NewId = () => string
export interface Ctx { selected: string | null; time: number; fps: number; newId: NewId }
export interface Clipboard { clip: TimelineClip; track: TrackId }
type Media = { kind: string; rel: string; name: string; duration?: number }

export const tracksOf = (tl: Timeline | null): Tracks => ({ V1: clipsOf(tl), A1: clipsOf(tl, "A1"), A2: clipsOf(tl, "A2") })

export function toTimeline(tl: Timeline, tr: Tracks): Timeline {
  return withTrack(withTrack(withTrack(tl, "V1", tr.V1), "A1", tr.A1), "A2", tr.A2)
}

export function trackOf(tr: Tracks, id: string | null): TrackId | null {
  if (!id) return null
  return (Object.keys(tr) as TrackId[]).find((k) => tr[k].some((c) => c.id === id)) ?? null
}

const isAudio = (t: TrackId | null): t is AudioTrack => t === "A1" || t === "A2"
const set = (tr: Tracks, t: TrackId, clips: TimelineClip[]): Tracks => (clips === tr[t] ? tr : { ...tr, [t]: clips })

/** Teilen, Q/W, Löschen, Verdoppeln, Einfügen. Kopieren/Rückgängig erledigt der Aufrufer. */
export function editTracks(tr: Tracks, a: EditAction, ctx: Ctx, board: Clipboard | null = null): Tracks {
  const { selected, time, fps, newId } = ctx
  const t = trackOf(tr, selected)
  const at = isAudio(t) ? t : "V1"
  if (a.kind === "split") return set(tr, at, isAudio(at) ? splitAudio(tr[at], time, fps, newId) : splitAt(tr.V1, time, fps, newId))
  if (a.kind === "split-keep") {
    return set(tr, at, isAudio(at) ? splitKeepAudio(tr[at], time, a.drop, fps, newId) : splitKeep(tr.V1, time, a.drop, fps, newId))
  }
  if (a.kind === "paste" && board) {
    if (isAudio(board.track)) return set(tr, board.track, dropAudio(tr[board.track], { ...board.clip, id: newId() }, time, fps))
    return set(tr, "V1", paste(tr.V1, board.clip, t === "V1" ? selected : null, fps, newId))
  }
  if (!selected || !t) return tr
  if (a.kind === "delete") return set(tr, t, isAudio(t) ? tr[t].filter((c) => c.id !== selected) : remove(tr.V1, selected, fps))
  if (a.kind === "duplicate") return set(tr, t, isAudio(t) ? duplicateAudio(tr[t], selected, fps, newId) : duplicate(tr.V1, selected, fps, newId))
  return tr
}

export function trimTracks(tr: Tracks, id: string, edge: "start" | "end", delta: number, fps: number,
  durations: Record<string, number>): Tracks {
  const t = trackOf(tr, id)
  if (!t) return tr
  return set(tr, t, isAudio(t) ? trimAudio(tr[t], id, edge, delta, fps, durations) : trim(tr.V1, id, edge, delta, fps, durations))
}

/** Tonclip auf eine Tonspur (auch die andere) an die Zeit `start` ziehen. Bildclips bleiben auf V1 (→ unverändert). */
export function moveAudioClip(tr: Tracks, id: string, to: AudioTrack, start: number, fps: number): Tracks {
  const from = trackOf(tr, id)
  if (!isAudio(from)) return tr
  if (from === to) return set(tr, to, moveAudio(tr[to], id, start, fps))
  const c = tr[from].find((x) => x.id === id)!
  return { ...tr, [from]: tr[from].filter((x) => x.id !== id), [to]: dropAudio(tr[to], c, start, fps) }
}

export function moveVideoClip(tr: Tracks, id: string, index: number, fps: number): Tracks {
  return trackOf(tr, id) === "V1" ? set(tr, "V1", moveTo(tr.V1, id, index, fps)) : tr
}

/** Medium aus der Bibliothek ablegen: Bild/Video an Stelle `index` auf V1, Ton auf seine Spur (oder `track`) ab `time`.
 *  Liefert die neuen Spuren und den neuen Clip, oder null, wenn das Medium nicht auf die Zeitleiste passt. */
export function addMedia(tr: Tracks, item: Media, at: { index?: number; time: number; track?: AudioTrack }, fps: number, newId: NewId):
  { tracks: Tracks; clip: TimelineClip } | null {
  const audio = audioTrackFor(item.kind)
  if (audio) {
    const track = at.track ?? audio
    const c = fromLibraryAudio(item, at.time, newId)!
    const next = dropAudio(tr[track], c, at.time, fps)
    return { tracks: { ...tr, [track]: next }, clip: next[next.length - 1] }
  }
  const c = fromLibrary(item, newId)
  if (!c) return null
  return { tracks: { ...tr, V1: append(tr.V1, c, at.index ?? tr.V1.length, fps) }, clip: c }
}

export const canSplit = (tr: Tracks, ctx: Ctx): boolean =>
  editTracks(tr, { kind: "split" }, { ...ctx, newId: () => "x" }) !== tr

export { AUDIO_TRACKS }
