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
import { musicClip, placeMusic, type MusicResult } from "./musicLogic"
import { mixerOf, setClipMix, setDuck, setTrackMix, type Mixer } from "./mixLogic"
import { unbind } from "./voiceBind"
import { timelineApi, type Timeline, type TrackId, type TrackMix } from "./timelineApi"

/** Verlaufszustand: Clips aller Spuren und Mischpult (5b) – Rückgängig gilt für beides. */
interface Snap { tracks: Tracks; mixer: Mixer }
const snapOf = (tl: Timeline | null): Snap => ({ tracks: tracksOf(tl), mixer: mixerOf(tl) })
function build(tl: Timeline, s: Snap): Timeline {
  let out = toTimeline(tl, s.tracks)
  for (const id of ["V1", "A1", "A2"] as const) out = setTrackMix(out, id, { gain_db: 0, mute: false, solo: false, ...s.mixer.tracks[id] })
  return setDuck(out, s.mixer.duck)
}

const newId = () => crypto.randomUUID().replace(/-/g, "")

/** Bearbeiten im Reiter „Schneiden“ (4b, 5a): Änderungen auf allen Spuren, Rückgängig/Wiederholen, automatisch
 *  speichern, Einrasten. `timeline` kommt aus useCut; eigene Änderungen behalten dessen `revision`, nur Laden vom
 *  Server setzt sie neu – daran erkennt der Hook, wann der Verlauf neu beginnt. Die echte revision fürs Speichern führt
 *  der AutoSaver. */
export function useCutEdit(projectId: string, timeline: Timeline | null, setTimeline: (t: Timeline) => void,
  selected: string | null, select: (id: string | null) => void, time: number, lengths: Record<string, number> = {}) {
  // `lengths`: echte Länge der Tondateien (media_rel → s, aus der Wellenform) – Grenze beim Kürzen
  const [hist] = useState(() => new History<Snap>(snapOf(null)))   // ein Objekt je Hook, Inhalt ändert sich
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
    hist.reset(snapOf(timeline))
    setFlags({ undo: false, redo: false })
  }
  useEffect(() => {
    if (!timeline || loadedFor.current === timeline.revision) return
    loadedFor.current = timeline.revision
    saver.current?.loaded(timeline)                                  // nur bei neuem Server-Stand, sonst gingen Änderungen verloren
  }, [timeline])

  const fps = timeline?.fps ?? 25
  const tracks = tracksOf(timeline)
  const mixer = mixerOf(timeline)

  const lastMix = useRef<string>("")                                 // Ziel des letzten Mischpult-Schritts (s. u.)
  const commit = useCallback((next: Snap, record = true) => {
    if (!timeline) return
    const tl = build(timeline, next)
    if (record) { hist.push(next); lastMix.current = "" }
    setTimeline(tl)
    saver.current?.change(tl)
    syncFlags()
  }, [timeline, setTimeline, hist, syncFlags])
  // Die Bearbeitungen (cutTracks) ziehen die an Shots gebundene Sprache selbst nach (5c)
  const apply = useCallback((next: Tracks, record = true) => commit({ tracks: next, mixer }, record), [commit, mixer])
  const change = useCallback((next: Tracks) => { if (next !== tracks) apply(next) }, [apply, tracks])

  const run = useCallback((a: EditAction) => {
    const h = hist
    if (a.kind === "undo" || a.kind === "redo") {
      if (a.kind === "undo" ? h.canUndo : h.canRedo) { lastMix.current = ""; commit(a.kind === "undo" ? h.undo() : h.redo(), false) }
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
  }, [commit, change, tracks, fps, selected, select, time, hist])

  // Kürzen: immer vom Stand beim Greifen aus (delta = Gesamtverschiebung), während des Ziehens ohne Verlaufsschritt,
  // beim Loslassen genau ein Schritt
  const onTrim = useCallback((id: string, edge: "start" | "end", delta: number, final: boolean) => {
    if (!trimFrom.current) trimFrom.current = tracks
    const known = { ...durations.current }                         // Medienlänge je Clip: Bibliothek, sonst Wellenform
    for (const c of [...trimFrom.current.A1, ...trimFrom.current.A2]) if (lengths[c.media_rel]) known[c.id] = lengths[c.media_rel]
    const next = trimTracks(trimFrom.current, id, edge, delta, fps, known)
    if (!final) { commit({ tracks: next, mixer }, false); return }                  // trimTracks zieht die Sprache schon mit
    const before = trimFrom.current
    trimFrom.current = null
    if (JSON.stringify(before) !== JSON.stringify(next)) { hist.push({ tracks: next, mixer }); lastMix.current = ""; commit({ tracks: next, mixer }, false) }
  }, [commit, tracks, fps, hist, lengths, mixer])

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

  /** Fertige Musik (5c-2) auf die Musik-Spur – ein Verlaufsschritt. false, wenn die Fassung noch nicht geladen ist. */
  const addMusic = useCallback((r: MusicResult): boolean => {
    const c = timeline ? musicClip(r, newId) : null
    if (!c) return false
    durations.current[c.id] = r.duration
    apply(placeMusic(tracks, c, r.scene_id, time, fps))
    select(c.id)
    return true
  }, [timeline, apply, tracks, time, fps, select])
  const move = useCallback((id: string, index: number) => change(moveVideoClip(tracks, id, index, fps)), [change, tracks, fps])
  const moveAudio = useCallback((id: string, track: AudioTrack, start: number) => change(moveAudioClip(tracks, id, track, start, fps)), [change, tracks, fps])
  // Mischpult (5b): Regler liefern beim Ziehen viele Werte – solange dasselbe Ziel weiter verstellt wird, ersetzt der
  // neue Wert den letzten Verlaufsschritt (ein Rückgängig nimmt die ganze Reglerbewegung zurück).
  const mixChange = useCallback((key: string, tl: Timeline) => {
    const next = snapOf(tl)
    if (lastMix.current === key && hist.canUndo) hist.replaceTop(next)
    else hist.push(next)
    lastMix.current = key
    commit(next, false)
  }, [commit, hist])
  const onTrackMix = useCallback((id: TrackId, v: TrackMix) => {
    if (!timeline) return
    const kind = "gain_db" in v ? "gain" : Object.keys(v)[0]
    mixChange(`track:${id}:${kind}`, setTrackMix(timeline, id, v))
  }, [timeline, mixChange])
  const onClipMix = useCallback((clipId: string, v: { gain_db?: number; fade_in?: number; fade_out?: number }) => {
    if (!timeline) return
    mixChange(`clip:${clipId}:${Object.keys(v)[0]}`, setClipMix(timeline, clipId, v))
  }, [timeline, mixChange])
  const onDuck = useCallback((on: boolean) => { if (timeline) mixChange(`duck:${on}`, setDuck(timeline, on)) }, [timeline, mixChange])
  const unbindVoice = useCallback((clipId: string) => change(unbind(tracks, clipId)), [change, tracks])
  const flush = useCallback(() => saver.current?.flush(), [])
  const learnDuration = useCallback((clipId: string, seconds: number) => { if (seconds > 0) durations.current[clipId] = seconds }, [])

  return {
    save, snap, toggleSnap: () => setSnap((s) => !s), run, onTrim, addMedia, addMusic, move, moveAudio, flush, learnDuration,
    mixer, onTrackMix, onClipMix, onDuck, unbindVoice,
    canUndo: flags.undo, canRedo: flags.redo,
    canSplit: canSplit(tracks, { selected, time, fps, newId }),
    snapTo: snap ? [time] : [],
  }
}
