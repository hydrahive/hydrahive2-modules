// Audio-Player-State über ein einzelnes <audio>-Element (kein externes Lib).
import { useCallback, useEffect, useRef, useState } from "react"
import { musicApi } from "./api"
import type { Track } from "./types"

export type RepeatMode = "off" | "all" | "one"

export interface PlayerUI {
  audioRef: React.RefObject<HTMLAudioElement | null>
  current: Track | null
  index: number
  playing: boolean
  currentTime: number
  duration: number
  volume: number
  shuffle: boolean
  repeat: RepeatMode
  select: (i: number) => void
  toggle: () => void
  prev: () => void
  next: () => void
  seek: (t: number) => void
  setVolume: (v: number) => void
  toggleShuffle: () => void
  cycleRepeat: () => void
}

const REPEAT_ORDER: RepeatMode[] = ["off", "all", "one"]

export function useAudioPlayer(tracks: Track[]): PlayerUI {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [index, setIndex] = useState(-1)
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVol] = useState(1)
  const [shuffle, setShuffle] = useState(false)
  const [repeat, setRepeat] = useState<RepeatMode>("off")

  const current = index >= 0 && index < tracks.length ? tracks[index] : null

  // Track-Wechsel: Quelle setzen und (falls vorher gespielt) weiterspielen.
  useEffect(() => {
    const a = audioRef.current
    if (!a || !current) return
    a.src = musicApi.streamUrl(current.id)
    a.load()
    if (playing) void a.play().catch(() => setPlaying(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const select = useCallback((i: number) => {
    setIndex(i)
    setPlaying(true)
  }, [])

  const toggle = useCallback(() => {
    const a = audioRef.current
    if (!a) return
    if (index < 0 && tracks.length > 0) { setIndex(0); setPlaying(true); return }
    if (a.paused) { void a.play().catch(() => {}); setPlaying(true) }
    else { a.pause(); setPlaying(false) }
  }, [index, tracks.length])

  // Nächster Index — berücksichtigt Shuffle (zufällig, nicht derselbe).
  const pickNext = useCallback((cur: number): number => {
    const n = tracks.length
    if (n === 0) return -1
    if (shuffle && n > 1) {
      let r = cur
      while (r === cur) r = Math.floor(Math.random() * n)
      return r
    }
    return (cur + 1) % n
  }, [shuffle, tracks.length])

  const next = useCallback(() => {
    if (tracks.length === 0) return
    setIndex((i) => pickNext(i))
    setPlaying(true)
  }, [tracks.length, pickNext])

  const prev = useCallback(() => {
    const n = tracks.length
    if (n === 0) return
    if (shuffle && n > 1) { setIndex((i) => pickNext(i)); setPlaying(true); return }
    setIndex((i) => (i <= 0 ? n - 1 : i - 1))
    setPlaying(true)
  }, [tracks.length, shuffle, pickNext])

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

  // Track-Ende: repeat-one wiederholt, repeat-off stoppt am Listenende, sonst weiter.
  const handleEnded = useCallback(() => {
    const a = audioRef.current
    if (!a) return
    if (repeat === "one") { a.currentTime = 0; void a.play().catch(() => {}); return }
    if (repeat === "off" && !shuffle && index === tracks.length - 1) {
      setPlaying(false)
      return
    }
    setIndex((i) => pickNext(i))
    setPlaying(true)
  }, [repeat, shuffle, index, tracks.length, pickNext])

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

  return {
    audioRef, current, index, playing, currentTime, duration, volume, shuffle, repeat,
    select, toggle, prev, next, seek, setVolume, toggleShuffle, cycleRepeat,
  }
}
