import { useCallback, useEffect, useRef, useState } from "react"
import { activeAt, filmLength, sourceTime } from "./cutLogic"
import type { TimelineClip } from "./timelineApi"

/** Wiedergabe der Schnittfassung (Etappe 4a; `clips` = Bildspur, `all` = alle Spuren für die Länge): eine eigene Uhr (requestAnimationFrame) führt; das sichtbare <video>
 *  folgt ihr. Beim Clipwechsel wird das Video an die Soll-Stelle gesetzt, sonst läuft es frei (kein „Daumenkino“).
 *  Idee wie im Kern-Videoschnitt (playbackSync.ts), eigene Umsetzung. */
export function useCutPlayer(clips: TimelineClip[], all: TimelineClip[] = clips) {
  const [time, setTime] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [rate, setRate] = useState(1)
  const video = useRef<HTMLVideoElement | null>(null)
  const clock = useRef({ t: 0, at: 0 })
  const total = filmLength(all)                          // Ton kann über das letzte Bild hinausreichen (5a)
  const current = activeAt(clips, time)

  const seek = useCallback((t: number) => {
    const v = Math.min(Math.max(0, t), total)
    clock.current = { t: v, at: performance.now() }
    setTime(v)
  }, [total])

  useEffect(() => {
    if (!playing) return
    clock.current = { t: time, at: performance.now() }
    let id = 0
    const tick = () => {
      const t = clock.current.t + ((performance.now() - clock.current.at) / 1000) * rate
      if (t >= total) { setTime(total); setPlaying(false); return }
      setTime(t)
      id = requestAnimationFrame(tick)
    }
    id = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(id)
    // Uhr nur bei Start/Stopp/Tempo neu aufsetzen, nicht bei jedem Bild
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, rate, total])

  // Sichtbares Video an die Uhr koppeln: Stelle setzen, wenn es zu weit weg ist (Clipwechsel, Springen, Pause).
  useEffect(() => {
    const el = video.current
    if (!el || current?.kind !== "video") return
    const want = sourceTime(current, time)
    if (Math.abs(el.currentTime - want) > (playing ? 0.3 : 0.04)) {
      try { el.currentTime = want } catch { /* Metadaten noch nicht da */ }
    }
    el.playbackRate = rate
    if (playing && el.paused) el.play().catch(() => { el.muted = true; el.play().catch(() => {}) })
    if (!playing && !el.paused) el.pause()
  }, [current, time, playing, rate])

  const toggle = useCallback(() => {
    if (!playing && time >= total) seek(0)
    setRate(1)
    setPlaying((p) => !p && total > 0)
  }, [playing, time, total, seek])

  const shuttle = useCallback((dir: 1 | -1) => {
    if (dir < 0) { seek(time - 5); return }
    setRate((r) => (playing ? Math.min(r * 2, 8) : 1))
    setPlaying(total > 0)
  }, [playing, time, total, seek])

  const bindVideo = useCallback((el: HTMLVideoElement | null) => { video.current = el }, [])
  return { time, total, playing, rate, current, seek, toggle, shuttle, bindVideo }
}
