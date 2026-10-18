/** Verdrahtung „Schneiden“ ↔ Bibliothek (4b, 5a): Ablegen aus der Bibliothek auf Bild- und Tonspuren. Hält StudioPage klein. */
import type { LibraryItem } from "./api"
import type { AudioEdit } from "./AudioTrack"
import type { AudioTrack } from "./cutAudio"
import type { TrackEdit } from "./CutTrack"

type AddMedia = (item: LibraryItem, index?: number, at?: number, track?: AudioTrack) => boolean
const isSound = (kind: string) => kind === "music" || kind === "audio"

/** Ränder aller Clips (Einrasten beim Verschieben auf den Tonspuren). */
export const edgesOf = (clips: { start: number; in: number; out: number }[]) => clips.flatMap((c) => [c.start, c.start + c.out - c.in])

export function cutDrops(items: LibraryItem[], ed: {
  move: TrackEdit["onMove"]; onTrim: TrackEdit["onTrim"]; moveAudio: AudioEdit["onMove"]; addMedia: AddMedia; snapTo: number[]; snap: boolean
}, clips: { start: number; in: number; out: number }[], notice: () => void): { edit: TrackEdit; audio: AudioEdit } {
  const find = (id: string) => items.find((i) => i.id === id)
  return {
    edit: { onMove: ed.move, onTrim: ed.onTrim, dropAt: null, snapTo: ed.snapTo,
      onDrop: (mediaId, index, at) => { const it = find(mediaId); if (it && !ed.addMedia(it, index, at)) notice() } },
    audio: { onMove: ed.moveAudio, onTrim: ed.onTrim, snapTo: ed.snapTo, edges: ed.snap ? edgesOf(clips) : [],
      onDrop: (mediaId, track, at) => { const it = find(mediaId); if (it && !ed.addMedia(it, undefined, at, isSound(it.kind) ? track : undefined)) notice() } },
  }
}

/** „Auf die Spur legen“ / „An die Zeitleiste anhängen“ in den Eigenschaften; liefert den Text-Schlüssel der Meldung. */
export function appendNotice(item: LibraryItem | null, add: AddMedia): string | null {
  if (!item || !add(item)) return null
  return isSound(item.kind) ? "cut_notice_sound" : "cut_notice_appended"
}
