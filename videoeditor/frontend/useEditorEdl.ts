import { useCallback, useRef, useState } from "react"
import type { Clip, EDL, VideoMeta } from "./types"
import { videoeditorApi } from "./api"

const HIST_MAX = 80
const SNAP_EPS = 0.05        // Sekunden-Toleranz für Keyframe-Snap-Anzeige
const AUTOSAVE_MS = 600

function uid(): string {
  return "c" + Math.random().toString(36).slice(2, 10)
}

function cloneClips(cs: Clip[]): Clip[] {
  return cs.map((c) => ({ ...c }))
}

/** Zentrale EDL-Verwaltung: Clips + Snap + Undo/Redo + debounced Auto-Save.
 *  Alle Schnitt-Mutationen laufen hierüber, damit History und Speichern an
 *  EINER Stelle sitzen (kein verstreuter State in der View). */
export function useEditorEdl(projectId: string, initial: VideoMeta) {
  const fileId = initial.file_id
  const keyframes = initial.keyframes ?? []

  const [clips, setClipsState] = useState<Clip[]>(initial.edl?.timeline ?? [])
  const [snapOn, setSnapOn] = useState<boolean>(() => {
    try { return JSON.parse(localStorage.getItem("videoeditor.snapOn") ?? "true") } catch { return true }
  })
  const [saved, setSaved] = useState(true)

  const history = useRef<Clip[][]>([])
  const future = useRef<Clip[][]>([])
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ---- Auto-Save (debounced) ------------------------------------------------
  const scheduleSave = useCallback((next: Clip[]) => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      const edl: EDL = { file_id: fileId, timeline: next }
      videoeditorApi.saveEdl(projectId, fileId, edl).then(() => setSaved(true)).catch(() => {})
    }, AUTOSAVE_MS)
  }, [projectId, fileId])

  const saveNow = useCallback(async () => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    await videoeditorApi.saveEdl(projectId, fileId, { file_id: fileId, timeline: clips })
    setSaved(true)
  }, [projectId, fileId, clips])

  // ---- History-gestützte Mutation ------------------------------------------
  const commit = useCallback((next: Clip[]) => {
    setClipsState((prev) => {
      history.current.push(cloneClips(prev))
      if (history.current.length > HIST_MAX) history.current.shift()
      future.current = []
      return next
    })
    setSaved(false)
    scheduleSave(next)
  }, [scheduleSave])

  const undo = useCallback(() => {
    setClipsState((prev) => {
      const h = history.current.pop()
      if (!h) return prev
      future.current.push(cloneClips(prev))
      setSaved(false)
      scheduleSave(h)
      return h
    })
  }, [scheduleSave])

  const redo = useCallback(() => {
    setClipsState((prev) => {
      const f = future.current.pop()
      if (!f) return prev
      history.current.push(cloneClips(prev))
      setSaved(false)
      scheduleSave(f)
      return f
    })
  }, [scheduleSave])

  // ---- Keyframe-Snap --------------------------------------------------------
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

  // ---- Schnitt-Operationen (alle über commit) ------------------------------
  const addRange = useCallback((start: number, end: number) => {
    const s = snapTime(start)
    const e = snapTime(end)
    if (e - s < 0.1) return
    // Beide Kanten auf Keyframe → verlustfrei kopierbar
    const mode: Clip["mode"] = (isOnKeyframe(s) && isOnKeyframe(e)) ? "copy" : "reencode"
    const clip: Clip = { id: uid(), src_start: Number(s.toFixed(3)), src_end: Number(e.toFixed(3)), mode }
    commit([...clips, clip].sort((a, b) => a.src_start - b.src_start))
    return clip.id
  }, [clips, commit, snapTime, isOnKeyframe])

  const splitAt = useCallback((t: number): string | null => {
    const target = clips.find((c) => t > c.src_start + 0.01 && t < c.src_end - 0.01)
    if (!target) return null
    const cut = snapTime(t)
    const right: Clip = { id: uid(), src_start: cut, src_end: target.src_end, mode: target.mode }
    commit(clips.flatMap((c) => c.id !== target.id ? [c] : [{ ...c, src_end: cut }, right]))
    return right.id
  }, [clips, commit, snapTime])

  const trim = useCallback((id: string, start: number, end: number) => {
    commit(clips.map((c) => c.id === id
      ? { ...c, src_start: Math.max(0, Math.min(start, end)), src_end: Math.max(start, end) }
      : c).sort((a, b) => a.src_start - b.src_start))
  }, [clips, commit])

  const remove = useCallback((id: string) => {
    commit(clips.filter((c) => c.id !== id))
  }, [clips, commit])

  const toggleMode = useCallback((id: string) => {
    commit(clips.map((c) => c.id === id ? { ...c, mode: c.mode === "copy" ? "reencode" : "copy" } : c))
  }, [clips, commit])

  return {
    clips, snapOn, saved, keyframes,
    snapTime, isOnKeyframe, toggleSnap,
    addRange, splitAt, trim, remove, toggleMode,
    undo, redo, saveNow,
    canUndo: history.current.length > 0, canRedo: future.current.length > 0,
  }
}
