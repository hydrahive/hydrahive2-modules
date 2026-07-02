import { useCallback, useEffect, useRef, useState } from "react"

/** Player-Steuerung: smoothe Playhead-Nadel via requestAnimationFrame (statt
 *  nur timeupdate ~200ms), Frame-Schritt, ±10s, Keyframe-Sprünge. Der Playhead
 *  wird bei laufender Wiedergabe mit ~60fps aktualisiert. */
export function usePlayer(
  videoRef: React.RefObject<HTMLVideoElement | null>,
  fps: number,
  duration: number,
  keyframes: number[],
  onTick?: (t: number) => void,
) {
  const [playhead, setPlayhead] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const rafRef = useRef<number>(0)
  const onTickRef = useRef(onTick)
  onTickRef.current = onTick

  const seek = useCallback((t: number) => {
    const clamped = Math.max(0, Math.min(duration, t))
    const v = videoRef.current
    if (v) v.currentTime = clamped
    setPlayhead(clamped)
  }, [videoRef, duration])

  const playPause = useCallback((play: boolean) => {
    const v = videoRef.current
    if (!v) return
    if (play) v.play().catch(() => {})
    else v.pause()
  }, [videoRef])

  const togglePlay = useCallback(() => {
    const v = videoRef.current
    if (!v) return
    if (v.paused) v.play().catch(() => {}); else v.pause()
  }, [videoRef])

  const nudge = useCallback((delta: number) => seek((videoRef.current?.currentTime ?? playhead) + delta), [seek, videoRef, playhead])
  const stepFrame = useCallback((dir: number) => nudge(dir / (fps || 25)), [nudge, fps])

  const jumpPrevKeyframe = useCallback(() => {
    if (!keyframes.length) return
    const before = keyframes.filter((k) => k < playhead - 0.05)
    seek(before.length ? before[before.length - 1] : keyframes[0])
  }, [keyframes, playhead, seek])

  const jumpNextKeyframe = useCallback(() => {
    if (!keyframes.length) return
    const after = keyframes.find((k) => k > playhead + 0.05)
    if (after != null) seek(after)
  }, [keyframes, playhead, seek])

  // smoothe Nadel via rAF, solange abgespielt wird
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    const smooth = () => {
      if (v.paused) return
      const t = v.currentTime
      setPlayhead(t)
      onTickRef.current?.(t)
      rafRef.current = requestAnimationFrame(smooth)
    }
    const onPlay = () => { setIsPlaying(true); cancelAnimationFrame(rafRef.current); rafRef.current = requestAnimationFrame(smooth) }
    const onPause = () => { setIsPlaying(false); cancelAnimationFrame(rafRef.current) }
    const onTimeUpdate = () => { if (v.paused) { setPlayhead(v.currentTime); onTickRef.current?.(v.currentTime) } }
    v.addEventListener("play", onPlay)
    v.addEventListener("pause", onPause)
    v.addEventListener("timeupdate", onTimeUpdate)
    return () => {
      v.removeEventListener("play", onPlay)
      v.removeEventListener("pause", onPause)
      v.removeEventListener("timeupdate", onTimeUpdate)
      cancelAnimationFrame(rafRef.current)
    }
  }, [videoRef])

  return { playhead, isPlaying, seek, playPause, togglePlay, nudge, stepFrame, jumpPrevKeyframe, jumpNextKeyframe }
}
