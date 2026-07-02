import { useCallback, useRef, useState } from "react"
import type { AudioTrack, Clip, EDL, OriginalAudio, VideoMeta } from "./types"
import { videoeditorApi } from "./api"
import * as A from "./_audioEdlOps"

const HIST_MAX = 80
const SNAP_EPS = 0.05        // Sekunden-Toleranz für Keyframe-Snap-Anzeige
const AUTOSAVE_MS = 600

function uid(): string {
  return "c" + Math.random().toString(36).slice(2, 10)
}

/** Vollständiger, undo-barer Editier-Zustand (Video-Clips + Audio). */
interface Snapshot {
  clips: Clip[]
  audioTracks: AudioTrack[]
  originalAudio: OriginalAudio
}

function cloneSnapshot(s: Snapshot): Snapshot {
  return {
    clips: s.clips.map((c) => ({ ...c })),
    audioTracks: A.cloneTracks(s.audioTracks),
    originalAudio: { ...s.originalAudio },
  }
}

/** Zentrale EDL-Verwaltung: Video-Clips + Audiospuren + Snap + Undo/Redo +
 *  debounced Auto-Save. Alle Mutationen laufen über commit(), damit History
 *  und Speichern (voller Snapshot) an EINER Stelle sitzen. */
export function useEditorEdl(projectId: string, initial: VideoMeta) {
  const fileId = initial.file_id
  const keyframes = initial.keyframes ?? []

  const [clips, setClips] = useState<Clip[]>(initial.edl?.timeline ?? [])
  const [audioTracks, setAudioTracks] = useState<AudioTrack[]>(initial.edl?.audio ?? [])
  const [originalAudio, setOriginalAudioState] = useState<OriginalAudio>(
    initial.edl?.original_audio ?? { mute: false, gain_db: 0 },
  )
  const [snapOn, setSnapOn] = useState<boolean>(() => {
    try { return JSON.parse(localStorage.getItem("videoeditor.snapOn") ?? "true") } catch { return true }
  })
  const [saved, setSaved] = useState(true)

  const history = useRef<Snapshot[]>([])
  const future = useRef<Snapshot[]>([])
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Aktuellen Zustand als Ref-Zugriff (für commit/save aus Callbacks heraus).
  const current = useRef<Snapshot>({ clips, audioTracks, originalAudio })
  current.current = { clips, audioTracks, originalAudio }

  // ---- Auto-Save (debounced) ------------------------------------------------
  const buildEdl = useCallback((s: Snapshot): EDL => ({
    file_id: fileId,
    timeline: s.clips,
    audio: s.audioTracks,
    original_audio: s.originalAudio,
  }), [fileId])

  const scheduleSave = useCallback((next: Snapshot) => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      videoeditorApi.saveEdl(projectId, fileId, buildEdl(next))
        .then(() => setSaved(true)).catch(() => {})
    }, AUTOSAVE_MS)
  }, [projectId, fileId, buildEdl])

  const saveNow = useCallback(async () => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    await videoeditorApi.saveEdl(projectId, fileId, buildEdl(current.current))
    setSaved(true)
  }, [projectId, fileId, buildEdl])

  // ---- History-gestützte Mutation ------------------------------------------
  const applySnapshot = useCallback((s: Snapshot) => {
    setClips(s.clips)
    setAudioTracks(s.audioTracks)
    setOriginalAudioState(s.originalAudio)
  }, [])

  /** Übernimmt eine partielle Änderung, pusht den vorherigen Zustand in die
   *  History und plant den Save. Alles über den vollen Snapshot. */
  const commit = useCallback((patch: Partial<Snapshot>) => {
    const prev = current.current
    history.current.push(cloneSnapshot(prev))
    if (history.current.length > HIST_MAX) history.current.shift()
    future.current = []
    const next: Snapshot = { ...prev, ...patch }
    applySnapshot(next)
    setSaved(false)
    scheduleSave(next)
  }, [applySnapshot, scheduleSave])

  const undo = useCallback(() => {
    const h = history.current.pop()
    if (!h) return
    future.current.push(cloneSnapshot(current.current))
    applySnapshot(h)
    setSaved(false)
    scheduleSave(h)
  }, [applySnapshot, scheduleSave])

  const redo = useCallback(() => {
    const f = future.current.pop()
    if (!f) return
    history.current.push(cloneSnapshot(current.current))
    applySnapshot(f)
    setSaved(false)
    scheduleSave(f)
  }, [applySnapshot, scheduleSave])

  // ---- Keyframe-Snap (auch für Audio-Kanten nutzbar) -----------------------
  const snapTime = useCallback((t: number): number => {
    if (!snapOn || keyframes.length === 0) return t
    let best = keyframes[0]
    let bestD = Math.abs(t - best)
    for (const k of keyframes) {
      const d = Math.abs(t - k)
      if (d < bestD) { best = k; bestD = d }
    }
    return best
  }, [snapOn, keyframes])

  const isOnKeyframe = useCallback((t: number): boolean =>
    keyframes.some((k) => Math.abs(k - t) <= SNAP_EPS), [keyframes])

  const toggleSnap = useCallback(() => {
    setSnapOn((v) => {
      const nv = !v
      try { localStorage.setItem("videoeditor.snapOn", JSON.stringify(nv)) } catch { /* ignore */ }
      return nv
    })
  }, [])

  // ---- Video-Schnitt-Operationen (alle über commit) ------------------------
  const addRange = useCallback((start: number, end: number) => {
    const s = snapTime(start), e = snapTime(end)
    if (e - s < 0.1) return
    const mode: Clip["mode"] = (isOnKeyframe(s) && isOnKeyframe(e)) ? "copy" : "reencode"
    const clip: Clip = { id: uid(), src_start: Number(s.toFixed(3)), src_end: Number(e.toFixed(3)), mode }
    commit({ clips: [...clips, clip].sort((a, b) => a.src_start - b.src_start) })
    return clip.id
  }, [clips, commit, snapTime, isOnKeyframe])

  const splitAt = useCallback((t: number): string | null => {
    const target = clips.find((c) => t > c.src_start + 0.01 && t < c.src_end - 0.01)
    if (!target) return null
    const cut = snapTime(t)
    const right: Clip = { id: uid(), src_start: cut, src_end: target.src_end, mode: target.mode }
    commit({ clips: clips.flatMap((c) => c.id !== target.id ? [c] : [{ ...c, src_end: cut }, right]) })
    return right.id
  }, [clips, commit, snapTime])

  const trim = useCallback((id: string, start: number, end: number) => {
    commit({ clips: clips.map((c) => c.id === id
      ? { ...c, src_start: Math.max(0, Math.min(start, end)), src_end: Math.max(start, end) }
      : c).sort((a, b) => a.src_start - b.src_start) })
  }, [clips, commit])

  const remove = useCallback((id: string) => {
    commit({ clips: clips.filter((c) => c.id !== id) })
  }, [clips, commit])

  const toggleMode = useCallback((id: string) => {
    commit({ clips: clips.map((c) => c.id === id ? { ...c, mode: c.mode === "copy" ? "reencode" : "copy" } : c) })
  }, [clips, commit])

  // ---- Audio-Operationen (über commit, delegiert an pure Ops) --------------
  const addTrack = useCallback((name?: string) =>
    commit({ audioTracks: A.addTrack(audioTracks, name) }), [audioTracks, commit])
  const removeTrack = useCallback((trackId: string) =>
    commit({ audioTracks: A.removeTrack(audioTracks, trackId) }), [audioTracks, commit])
  const renameTrack = useCallback((trackId: string, name: string) =>
    commit({ audioTracks: A.renameTrack(audioTracks, trackId, name) }), [audioTracks, commit])
  const setTrackFlag = useCallback((trackId: string, flags: { mute?: boolean; solo?: boolean }) =>
    commit({ audioTracks: A.setTrackFlag(audioTracks, trackId, flags) }), [audioTracks, commit])
  const setTrackGain = useCallback((trackId: string, db: number) =>
    commit({ audioTracks: A.setTrackGain(audioTracks, trackId, db) }), [audioTracks, commit])

  const addAudioClip = useCallback((trackId: string, sourceRel: string, tStart: number, duration: number) =>
    commit({ audioTracks: A.addClip(audioTracks, trackId, sourceRel, snapTime(tStart), duration) }),
    [audioTracks, commit, snapTime])
  const moveAudioClip = useCallback((trackId: string, clipId: string, tStart: number) =>
    commit({ audioTracks: A.moveClip(audioTracks, trackId, clipId, snapTime(tStart)) }),
    [audioTracks, commit, snapTime])
  const trimAudioClip = useCallback((trackId: string, clipId: string, srcStart: number, srcEnd: number) =>
    commit({ audioTracks: A.trimClip(audioTracks, trackId, clipId, srcStart, srcEnd) }), [audioTracks, commit])
  const splitAudioClipAt = useCallback((trackId: string, clipId: string, tSplit: number) =>
    commit({ audioTracks: A.splitClipAt(audioTracks, trackId, clipId, snapTime(tSplit)) }),
    [audioTracks, commit, snapTime])
  const removeAudioClip = useCallback((trackId: string, clipId: string) =>
    commit({ audioTracks: A.removeClip(audioTracks, trackId, clipId) }), [audioTracks, commit])
  const setClipGain = useCallback((trackId: string, clipId: string, db: number) =>
    commit({ audioTracks: A.setClipGain(audioTracks, trackId, clipId, db) }), [audioTracks, commit])
  const setClipFade = useCallback((trackId: string, clipId: string, fade: { fadeIn?: number; fadeOut?: number }) =>
    commit({ audioTracks: A.setClipFade(audioTracks, trackId, clipId, fade) }), [audioTracks, commit])

  const setOriginalAudio = useCallback((patch: { mute?: boolean; gain_db?: number }) =>
    commit({ originalAudio: {
      mute: patch.mute ?? originalAudio.mute,
      gain_db: patch.gain_db ?? originalAudio.gain_db,
    } }), [originalAudio, commit])

  return {
    clips, audioTracks, originalAudio, snapOn, saved, keyframes,
    snapTime, isOnKeyframe, toggleSnap,
    addRange, splitAt, trim, remove, toggleMode,
    addTrack, removeTrack, renameTrack, setTrackFlag, setTrackGain,
    addAudioClip, moveAudioClip, trimAudioClip, splitAudioClipAt,
    removeAudioClip, setClipGain, setClipFade, setOriginalAudio,
    undo, redo, saveNow,
    canUndo: history.current.length > 0, canRedo: future.current.length > 0,
  }
}
