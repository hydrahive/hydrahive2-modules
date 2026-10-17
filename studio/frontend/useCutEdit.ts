import { useCallback, useEffect, useRef, useState } from "react"
import type { LibraryItem } from "./api"
import { append, duplicate, fromLibrary, moveTo, paste, remove, splitAt, splitKeep, trim } from "./cutEdit"
import { History } from "./cutHistory"
import type { EditAction } from "./cutKeys"
import { AutoSaver, type SaveState } from "./cutSave"
import { clipsOf, timelineApi, type Timeline, type TimelineClip } from "./timelineApi"

const newId = () => crypto.randomUUID().replace(/-/g, "")

/** Bearbeiten im Reiter „Schneiden“ (4b): Änderungen, Rückgängig/Wiederholen, automatisch speichern, Einrasten.
 *  `timeline` kommt aus useCut; eigene Änderungen behalten dessen `revision`, nur Laden vom Server setzt sie neu –
 *  daran erkennt der Hook, wann der Verlauf neu beginnt. Die echte revision fürs Speichern führt der AutoSaver. */
export function useCutEdit(projectId: string, timeline: Timeline | null, setTimeline: (t: Timeline) => void,
  selected: string | null, select: (id: string | null) => void, time: number) {
  const [hist] = useState(() => new History<TimelineClip[]>([]))   // ein Objekt je Hook, Inhalt ändert sich
  const loadedFor = useRef<number | null>(null)
  const saver = useRef<AutoSaver | null>(null)
  const clipboard = useRef<TimelineClip | null>(null)
  const durations = useRef<Record<string, number>>({})
  const trimFrom = useRef<TimelineClip[] | null>(null)
  const [save, setSave] = useState<SaveState>("saved")
  const [snap, setSnap] = useState(true)
  const [flags, setFlags] = useState({ undo: false, redo: false })
  const [seen, setSeen] = useState<number | null>(null)            // revision des zuletzt geladenen Stands
  const syncFlags = useCallback(() => setFlags({ undo: hist.canUndo, redo: hist.canRedo }), [hist])

  useEffect(() => {
    const s = new AutoSaver((tl) => timelineApi.save(projectId, tl), setSave)
    saver.current = s
    return () => { void s.flush() }                                   // Reiter verlassen / Projekt wechseln → sofort speichern
  }, [projectId])

  // Frisch vom Server (Laden, Übernehmen, Neu laden): Verlauf neu beginnen. Eigene Änderungen behalten die revision
  // aus useCut – nur ein neuer Stand vom Server ändert sie.
  if (timeline && timeline.revision !== seen) {
    setSeen(timeline.revision)
    hist.reset(clipsOf(timeline))
    setFlags({ undo: false, redo: false })
  }
  useEffect(() => {
    if (!timeline || loadedFor.current === timeline.revision) return
    loadedFor.current = timeline.revision
    saver.current?.loaded(timeline)                                  // nur bei neuem Server-Stand, sonst gingen Änderungen verloren
  }, [timeline])

  const fps = timeline?.fps ?? 25
  const clips = clipsOf(timeline)

  const apply = useCallback((next: TimelineClip[], record = true) => {
    if (!timeline) return
    const tl: Timeline = { ...timeline, tracks: [{ id: "V1", kind: "video", clips: next }] }
    if (record) hist.push(next)
    setTimeline(tl)
    saver.current?.change(tl)
    syncFlags()
  }, [timeline, setTimeline, hist, syncFlags])

  const run = useCallback((a: EditAction) => {
    const h = hist
    if (a.kind === "undo" || a.kind === "redo") {
      if (a.kind === "undo" ? h.canUndo : h.canRedo) apply(a.kind === "undo" ? h.undo() : h.redo(), false)
      return
    }
    if (a.kind === "split") return apply(splitAt(clips, time, fps, newId))
    if (a.kind === "split-keep") return apply(splitKeep(clips, time, a.drop, fps, newId))
    if (a.kind === "copy") { clipboard.current = clips.find((c) => c.id === selected) ?? null; return }
    if (a.kind === "paste") { if (clipboard.current) apply(paste(clips, clipboard.current, selected, fps, newId)); return }
    if (!selected) return
    if (a.kind === "delete") { apply(remove(clips, selected, fps)); select(null) }
    else if (a.kind === "duplicate") apply(duplicate(clips, selected, fps, newId))
  }, [apply, clips, fps, selected, select, time, hist])

  // Kürzen: immer vom Stand beim Greifen aus (delta = Gesamtverschiebung), während des Ziehens ohne Verlaufsschritt,
  // beim Loslassen genau ein Schritt
  const onTrim = useCallback((id: string, edge: "start" | "end", delta: number, final: boolean) => {
    if (!trimFrom.current) trimFrom.current = clips
    const next = trim(trimFrom.current, id, edge, delta, fps, durations.current)
    if (!final) { apply(next, false); return }
    const before = trimFrom.current
    trimFrom.current = null
    if (JSON.stringify(before) !== JSON.stringify(next)) { hist.push(next); apply(next, false) }
  }, [apply, clips, fps, hist])

  const addMedia = useCallback((item: LibraryItem, index?: number): boolean => {
    const c = fromLibrary(item, newId)
    if (!c) return false
    if (item.kind === "video" && item.duration) durations.current[c.id] = item.duration
    apply(append(clips, c, index ?? clips.length, fps))
    select(c.id)
    return true
  }, [apply, clips, fps, select])

  const move = useCallback((id: string, index: number) => apply(moveTo(clips, id, index, fps)), [apply, clips, fps])
  const flush = useCallback(() => saver.current?.flush(), [])
  const learnDuration = useCallback((clipId: string, seconds: number) => { if (seconds > 0) durations.current[clipId] = seconds }, [])

  return {
    save, snap, toggleSnap: () => setSnap((s) => !s), run, onTrim, addMedia, move, flush, learnDuration,
    canUndo: flags.undo, canRedo: flags.redo,
    canSplit: splitAt(clips, time, fps, () => "x") !== clips,
    snapTo: snap ? [time] : [],
  }
}
