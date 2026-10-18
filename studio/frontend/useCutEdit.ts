import { useCallback, useEffect, useRef, useState } from "react"
import type { LibraryItem } from "./api"
import { needsLength, withLength, type AudioTrack } from "./cutAudio"
import { History } from "./cutHistory"
import type { EditAction } from "./cutKeys"
import { AutoSaver, type SaveState } from "./cutSave"
import {
  addMedia as addTo, canSplit, editTracks, moveAudioClip, moveVideoClip, toTimeline, trackOf, tracksOf, trimTracks,
  type Clipboard, type Tracks,
} from "./cutTracks"
import { timelineApi, type Timeline } from "./timelineApi"

const newId = () => crypto.randomUUID().replace(/-/g, "")

/** Bearbeiten im Reiter „Schneiden“ (4b, 5a): Änderungen auf allen Spuren, Rückgängig/Wiederholen, automatisch
 *  speichern, Einrasten. `timeline` kommt aus useCut; eigene Änderungen behalten dessen `revision`, nur Laden vom
 *  Server setzt sie neu – daran erkennt der Hook, wann der Verlauf neu beginnt. Die echte revision fürs Speichern führt
 *  der AutoSaver. */
export function useCutEdit(projectId: string, timeline: Timeline | null, setTimeline: (t: Timeline) => void,
  selected: string | null, select: (id: string | null) => void, time: number, lengths: Record<string, number> = {}) {
  // `lengths`: echte Länge der Tondateien (media_rel → s, aus der Wellenform) – Grenze beim Kürzen
  const [hist] = useState(() => new History<Tracks>(tracksOf(null)))   // ein Objekt je Hook, Inhalt ändert sich
  const loadedFor = useRef<number | null>(null)
  const saver = useRef<AutoSaver | null>(null)
  const clipboard = useRef<Clipboard | null>(null)
  const durations = useRef<Record<string, number>>({})
  const trimFrom = useRef<Tracks | null>(null)
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
    hist.reset(tracksOf(timeline))
    setFlags({ undo: false, redo: false })
  }
  useEffect(() => {
    if (!timeline || loadedFor.current === timeline.revision) return
    loadedFor.current = timeline.revision
    saver.current?.loaded(timeline)                                  // nur bei neuem Server-Stand, sonst gingen Änderungen verloren
  }, [timeline])

  const fps = timeline?.fps ?? 25
  const tracks = tracksOf(timeline)

  const apply = useCallback((next: Tracks, record = true) => {
    if (!timeline) return
    const tl = toTimeline(timeline, next)
    if (record) hist.push(next)
    setTimeline(tl)
    saver.current?.change(tl)
    syncFlags()
  }, [timeline, setTimeline, hist, syncFlags])
  const change = useCallback((next: Tracks) => { if (next !== tracks) apply(next) }, [apply, tracks])

  const run = useCallback((a: EditAction) => {
    const h = hist
    if (a.kind === "undo" || a.kind === "redo") {
      if (a.kind === "undo" ? h.canUndo : h.canRedo) apply(a.kind === "undo" ? h.undo() : h.redo(), false)
      return
    }
    if (a.kind === "copy") {
      const t = trackOf(tracks, selected)
      const c = t ? tracks[t].find((x) => x.id === selected) : undefined
      clipboard.current = t && c ? { clip: c, track: t } : null
      return
    }
    const next = editTracks(tracks, a, { selected, time, fps, newId }, clipboard.current)
    change(next)
    if (a.kind === "delete" && next !== tracks) select(null)
  }, [apply, change, tracks, fps, selected, select, time, hist])

  // Kürzen: immer vom Stand beim Greifen aus (delta = Gesamtverschiebung), während des Ziehens ohne Verlaufsschritt,
  // beim Loslassen genau ein Schritt
  const onTrim = useCallback((id: string, edge: "start" | "end", delta: number, final: boolean) => {
    if (!trimFrom.current) trimFrom.current = tracks
    const known = { ...durations.current }                         // Medienlänge je Clip: Bibliothek, sonst Wellenform
    for (const c of [...trimFrom.current.A1, ...trimFrom.current.A2]) if (lengths[c.media_rel]) known[c.id] = lengths[c.media_rel]
    const next = trimTracks(trimFrom.current, id, edge, delta, fps, known)
    if (!final) { apply(next, false); return }
    const before = trimFrom.current
    trimFrom.current = null
    if (JSON.stringify(before) !== JSON.stringify(next)) { hist.push(next); apply(next, false) }
  }, [apply, tracks, fps, hist, lengths])

  /** Medium ablegen: Bild/Video an Stelle `index` auf V1, Ton ab `at` (Standard: Abspielkopf) auf seine Spur. */
  const place = useCallback((item: LibraryItem, index?: number, at?: number, track?: AudioTrack): boolean => {
    const r = addTo(tracks, item, { index, time: at ?? time, track }, fps, newId)
    if (!r) return false
    if (item.duration) durations.current[r.clip.id] = item.duration
    apply(r.tracks)
    select(r.clip.id)
    return true
  }, [apply, tracks, fps, select, time])
  const placeLatest = useRef(place)
  useEffect(() => { placeLatest.current = place })

  /** Kennt die Bibliothek die Länge eines Tons nicht, wird sie zuerst gemessen (Spec 5a „Länge eines Tonclips“) –
   *  sonst entstünde ein zu langer Clip. Danach legt der jeweils aktuelle Stand ab (placeLatest). */
  const addMedia = useCallback((item: LibraryItem, index?: number, at?: number, track?: AudioTrack): boolean => {
    if (!needsLength(item)) return place(item, index, at, track)
    const when = at ?? time
    timelineApi.waveform(projectId, item.rel)
      .then((w) => placeLatest.current(withLength(item, w.duration), index, when, track),
        () => placeLatest.current(item, index, when, track))
    return true
  }, [place, projectId, time])

  const move = useCallback((id: string, index: number) => change(moveVideoClip(tracks, id, index, fps)), [change, tracks, fps])
  const moveAudio = useCallback((id: string, track: AudioTrack, start: number) => change(moveAudioClip(tracks, id, track, start, fps)), [change, tracks, fps])
  const flush = useCallback(() => saver.current?.flush(), [])
  const learnDuration = useCallback((clipId: string, seconds: number) => { if (seconds > 0) durations.current[clipId] = seconds }, [])

  return {
    save, snap, toggleSnap: () => setSnap((s) => !s), run, onTrim, addMedia, move, moveAudio, flush, learnDuration,
    canUndo: flags.undo, canRedo: flags.redo,
    canSplit: canSplit(tracks, { selected, time, fps, newId }),
    snapTo: snap ? [time] : [],
  }
}
