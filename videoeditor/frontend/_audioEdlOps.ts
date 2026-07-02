import type { AudioClip, AudioTrack } from "./types"

/** Pure Transformationen auf AudioTrack[]. Keine React-/Save-Logik hier —
 *  der Hook (useEditorEdl) wickelt History + Auto-Save um diese Funktionen. */

export function uid(): string {
  return "a" + Math.random().toString(36).slice(2, 10)
}

export function cloneTracks(ts: AudioTrack[]): AudioTrack[] {
  return ts.map((t) => ({ ...t, clips: t.clips.map((c) => ({ ...c })) }))
}

export function addTrack(tracks: AudioTrack[], name?: string): AudioTrack[] {
  const t: AudioTrack = {
    id: uid(),
    name: name ?? `Spur ${tracks.length + 1}`,
    mute: false,
    solo: false,
    gain_db: 0,
    clips: [],
  }
  return [...tracks, t]
}

export function removeTrack(tracks: AudioTrack[], trackId: string): AudioTrack[] {
  return tracks.filter((t) => t.id !== trackId)
}

export function renameTrack(tracks: AudioTrack[], trackId: string, name: string): AudioTrack[] {
  return tracks.map((t) => (t.id === trackId ? { ...t, name } : t))
}

export function setTrackFlag(
  tracks: AudioTrack[],
  trackId: string,
  flags: { mute?: boolean; solo?: boolean },
): AudioTrack[] {
  return tracks.map((t) =>
    t.id === trackId
      ? { ...t, mute: flags.mute ?? t.mute, solo: flags.solo ?? t.solo }
      : t,
  )
}

export function setTrackGain(tracks: AudioTrack[], trackId: string, db: number): AudioTrack[] {
  return tracks.map((t) => (t.id === trackId ? { ...t, gain_db: db } : t))
}

// ---- Clip-Operationen -------------------------------------------------------

function mapTrack(
  tracks: AudioTrack[],
  trackId: string,
  fn: (clips: AudioClip[]) => AudioClip[],
): AudioTrack[] {
  return tracks.map((t) => (t.id === trackId ? { ...t, clips: fn(t.clips) } : t))
}

export function addClip(
  tracks: AudioTrack[],
  trackId: string,
  sourceRel: string,
  tStart: number,
  duration: number,
): AudioTrack[] {
  const clip: AudioClip = {
    id: uid(),
    source_rel: sourceRel,
    t_start: Math.max(0, tStart),
    src_start: 0,
    src_end: duration,
    gain_db: 0,
    fade_in: 0,
    fade_out: 0,
  }
  return mapTrack(tracks, trackId, (cs) =>
    [...cs, clip].sort((a, b) => a.t_start - b.t_start),
  )
}

export function moveClip(
  tracks: AudioTrack[],
  trackId: string,
  clipId: string,
  tStart: number,
): AudioTrack[] {
  return mapTrack(tracks, trackId, (cs) =>
    cs
      .map((c) => (c.id === clipId ? { ...c, t_start: Math.max(0, tStart) } : c))
      .sort((a, b) => a.t_start - b.t_start),
  )
}

export function trimClip(
  tracks: AudioTrack[],
  trackId: string,
  clipId: string,
  srcStart: number,
  srcEnd: number,
): AudioTrack[] {
  return mapTrack(tracks, trackId, (cs) =>
    cs.map((c) =>
      c.id === clipId
        ? { ...c, src_start: Math.max(0, Math.min(srcStart, srcEnd)), src_end: Math.max(srcStart, srcEnd) }
        : c,
    ),
  )
}

export function splitClipAt(
  tracks: AudioTrack[],
  trackId: string,
  clipId: string,
  tSplit: number,
): AudioTrack[] {
  return mapTrack(tracks, trackId, (cs) => {
    const target = cs.find((c) => c.id === clipId)
    if (!target) return cs
    const clipDur = target.src_end - target.src_start
    const localOffset = tSplit - target.t_start
    if (localOffset <= 0.01 || localOffset >= clipDur - 0.01) return cs
    const cutSrc = target.src_start + localOffset
    const right: AudioClip = {
      ...target,
      id: uid(),
      t_start: tSplit,
      src_start: cutSrc,
      fade_in: 0,
    }
    const left: AudioClip = { ...target, src_end: cutSrc, fade_out: 0 }
    return cs
      .flatMap((c) => (c.id !== clipId ? [c] : [left, right]))
      .sort((a, b) => a.t_start - b.t_start)
  })
}

export function removeClip(tracks: AudioTrack[], trackId: string, clipId: string): AudioTrack[] {
  return mapTrack(tracks, trackId, (cs) => cs.filter((c) => c.id !== clipId))
}

export function setClipGain(
  tracks: AudioTrack[],
  trackId: string,
  clipId: string,
  db: number,
): AudioTrack[] {
  return mapTrack(tracks, trackId, (cs) =>
    cs.map((c) => (c.id === clipId ? { ...c, gain_db: db } : c)),
  )
}

export function setClipFade(
  tracks: AudioTrack[],
  trackId: string,
  clipId: string,
  fade: { fadeIn?: number; fadeOut?: number },
): AudioTrack[] {
  return mapTrack(tracks, trackId, (cs) =>
    cs.map((c) =>
      c.id === clipId
        ? {
            ...c,
            fade_in: fade.fadeIn ?? c.fade_in,
            fade_out: fade.fadeOut ?? c.fade_out,
          }
        : c,
    ),
  )
}
