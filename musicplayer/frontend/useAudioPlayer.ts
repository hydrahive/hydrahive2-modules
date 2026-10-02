// Audio-Player-State über ein einzelnes <audio>-Element (kein externes Lib).
// Lebt in der Projektansicht, damit die Musik beim Umschalten auf Video weiterläuft.
import { useCallback, useEffect, useRef, useState } from "react"
import { musicApi } from "./api"
import { afterEnded, currentOf, nextId, prevId, type Order, type RepeatMode } from "./playlist"
import type { Track } from "./types"

export type { RepeatMode } from "./playlist"

export interface PlayerUI {
  audioRef: React.RefObject<HTMLAudioElement | null>
  activeTrack: Track | null
  playing: boolean
  elapsed: number
  duration: number
  volume: number
  shuffle: boolean
  repeat: RepeatMode
  select: (id: number) => void
  toggle: () => void
  pause: () => void
  /** Weiter an derselben Stelle (nach dem Video); tut nichts ohne gewähltes Lied. */
  resume: () => void
  prev: () => void
  next: () => void
  seek: (t: number) => void
  setVolume: (v: number) => void
  toggleShuffle: () => void
  cycleRepeat: () => void
}

const REPEAT_ORDER: RepeatMode[] = ["off", "all", "one"]

export function useAudioPlayer(projectId: string, tracks: Track[]): PlayerUI {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVol] = useState(1)
  const [shuffle, setShuffle] = useState(false)
  const [repeat, setRepeat] = useState<RepeatMode>("off")

  const current = currentOf(tracks, currentId)
  const order: Order = { shuffle, random: Math.random }

  // Quelle wechseln (neues Lied) oder stoppen (Lied gelöscht). Weiterspielen, falls vorher gespielt.
  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    if (!current) {
      if (a.getAttribute("src")) { a.pause(); a.removeAttribute("src"); a.load() }
      return
    }
    a.src = musicApi.streamUrl(projectId, current.id)
    a.load()
    if (playing) void a.play().catch(() => setPlaying(false))
    // `playing` absichtlich nicht als Abhängigkeit: der Effekt reagiert nur auf Quellenwechsel.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, current?.id])

  const select = useCallback((id: number) => { setCurrentId(id); setPlaying(true) }, [])

  const toggle = useCallback(() => {
    const a = audioRef.current
    if (!a) return
    if (!current) {
      const first = nextId(tracks, null, { shuffle: false, random: Math.random })
      if (first !== null) { setCurrentId(first); setPlaying(true) }
      return
    }
    if (a.paused) { void a.play().catch(() => {}); setPlaying(true) }
    else { a.pause(); setPlaying(false) }
  }, [current, tracks])

  const pause = useCallback(() => { audioRef.current?.pause() }, [])
  const resume = useCallback(() => {
    const a = audioRef.current
    if (a && a.getAttribute("src") && a.paused) void a.play().catch(() => {})
  }, [])

  const step = (pick: typeof nextId) => {
    const id = pick(tracks, current?.id ?? null, order)
    if (id !== null) { setCurrentId(id); setPlaying(true) }
  }
  const next = () => step(nextId)
  const prev = () => step(prevId)

  const seek = useCallback((t: number) => {
    const a = audioRef.current
    if (a) { a.currentTime = t; setCurrentTime(t) }
  }, [])

  const setVolume = useCallback((v: number) => {
    const a = audioRef.current
    if (a) a.volume = v
    setVol(v)
  }, [])

  const toggleShuffle = useCallback(() => setShuffle((s) => !s), [])
  const cycleRepeat = useCallback(
    () => setRepeat((r) => REPEAT_ORDER[(REPEAT_ORDER.indexOf(r) + 1) % REPEAT_ORDER.length]),
    [],
  )

  const handleEnded = useCallback(() => {
    const a = audioRef.current
    if (!a) return
    const action = afterEnded(tracks, currentId, repeat, { shuffle, random: Math.random })
    if (action.kind === "repeat") { a.currentTime = 0; void a.play().catch(() => {}); return }
    if (action.kind === "stop") { setPlaying(false); return }
    setCurrentId(action.id)
    setPlaying(true)
  }, [tracks, currentId, repeat, shuffle])

  // Audio-Events an den State binden.
  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    const onTime = () => setCurrentTime(a.currentTime)
    const onMeta = () => setDuration(a.duration || 0)
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    a.addEventListener("timeupdate", onTime)
    a.addEventListener("loadedmetadata", onMeta)
    a.addEventListener("ended", handleEnded)
    a.addEventListener("play", onPlay)
    a.addEventListener("pause", onPause)
    return () => {
      a.removeEventListener("timeupdate", onTime)
      a.removeEventListener("loadedmetadata", onMeta)
      a.removeEventListener("ended", handleEnded)
      a.removeEventListener("play", onPlay)
      a.removeEventListener("pause", onPause)
    }
  }, [handleEnded])

  // Beim Projektwechsel wird die keyed Project-View ausgehängt: Wiedergabe sicher stoppen.
  useEffect(() => () => {
    const audio = audioRef.current
    if (!audio) return
    audio.pause()
    audio.removeAttribute("src")
    audio.load()
  }, [])

  return {
    audioRef, activeTrack: current, playing, elapsed: currentTime, duration, volume, shuffle, repeat,
    select, toggle, pause, resume, prev, next, seek, setVolume, toggleShuffle, cycleRepeat,
  }
}
