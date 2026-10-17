import { useCallback, useEffect, useRef, useState } from "react"

/** Steuerung eines echten <video>/<audio> (Etappe 1). Zeit, Abspielen, Spulen (J/L verdoppeln die Geschwindigkeit). */
export function usePlayer(key: string | null) {
  const ref = useRef<HTMLMediaElement | null>(null)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [playing, setPlaying] = useState(false)

  const bind = useCallback((el: HTMLMediaElement | null) => {
    ref.current = el
    if (!el) return
    el.ontimeupdate = () => setTime(el.currentTime)
    el.onloadedmetadata = () => setDuration(Number.isFinite(el.duration) ? el.duration : 0)
    el.onplay = () => setPlaying(true)
    el.onpause = () => setPlaying(false)
    el.onended = () => setPlaying(false)
  }, [])

  useEffect(() => {
    const reset = window.setTimeout(() => { setTime(0); setDuration(0); setPlaying(false) }, 0)
    return () => window.clearTimeout(reset)
  }, [key])

  const seek = useCallback((t: number) => {
    const el = ref.current
    if (!el) return
    el.currentTime = Math.min(Math.max(0, t), Number.isFinite(el.duration) ? el.duration : t)
    setTime(el.currentTime)
  }, [])

  const toggle = useCallback(() => {
    const el = ref.current
    if (!el) return
    el.playbackRate = 1
    if (el.paused) void el.play().catch(() => {})
    else el.pause()
  }, [])

  /** Vorspulen schneller (1×, 2×, 4×, 8×). Zurückspulen kann der Browser nicht – dort springt J 5 Sekunden zurück. */
  const shuttle = useCallback((dir: 1 | -1) => {
    const el = ref.current
    if (!el) return
    if (dir < 0) { seek(el.currentTime - 5); return }
    el.playbackRate = el.paused ? 1 : Math.min(el.playbackRate * 2, 8)
    if (el.paused) void el.play().catch(() => {})
  }, [seek])

  return { bind, time, duration, playing, seek, toggle, shuttle, has: () => !!ref.current }
}
