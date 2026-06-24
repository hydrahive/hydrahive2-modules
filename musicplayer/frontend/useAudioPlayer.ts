// Audio-Player-State über ein einzelnes <audio>-Element (kein externes Lib).
import { useCallback, useEffect, useRef, useState } from "react"
import { musicApi } from "./api"
import type { Track } from "./types"

export interface PlayerUI {
  audioRef: React.RefObject<HTMLAudioElement | null>
  current: Track | null
  index: number
  playing: boolean
  currentTime: number
  duration: number
  volume: number
  select: (i: number) => void
  toggle: () => void
  prev: () => void
  next: () => void
  seek: (t: number) => void
  setVolume: (v: number) => void
}

export function useAudioPlayer(tracks: Track[]): PlayerUI {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [index, setIndex] = useState(-1)
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVol] = useState(1)

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

  const next = useCallback(() => {
    if (tracks.length === 0) return
    setIndex((i) => (i + 1) % tracks.length)
    setPlaying(true)
  }, [tracks.length])

  const prev = useCallback(() => {
    if (tracks.length === 0) return
    setIndex((i) => (i <= 0 ? tracks.length - 1 : i - 1))
    setPlaying(true)
  }, [tracks.length])

  const seek = useCallback((t: number) => {
    const a = audioRef.current
    if (a) { a.currentTime = t; setCurrentTime(t) }
  }, [])

  const setVolume = useCallback((v: number) => {
    const a = audioRef.current
    if (a) a.volume = v
    setVol(v)
  }, [])

  // Audio-Events an den State binden.
  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    const onTime = () => setCurrentTime(a.currentTime)
    const onMeta = () => setDuration(a.duration || 0)
    const onEnd = () => next()
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    a.addEventListener("timeupdate", onTime)
    a.addEventListener("loadedmetadata", onMeta)
    a.addEventListener("ended", onEnd)
    a.addEventListener("play", onPlay)
    a.addEventListener("pause", onPause)
    return () => {
      a.removeEventListener("timeupdate", onTime)
      a.removeEventListener("loadedmetadata", onMeta)
      a.removeEventListener("ended", onEnd)
      a.removeEventListener("play", onPlay)
      a.removeEventListener("pause", onPause)
    }
  }, [next])

  return {
    audioRef, current, index, playing, currentTime, duration, volume,
    select, toggle, prev, next, seek, setVolume,
  }
}
