import { useEffect, useRef, useState } from "react"
import { audioUrl } from "./api"

/** EIN <audio> für die ganze Bibliothek: immer nur ein Titel spielt, keine 17 Player-Balken untereinander. */
export function useSinglePlayer(projectId: string) {
  const ref = useRef<HTMLAudioElement>(null)
  const [current, setCurrent] = useState<string | null>(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    ref.current?.pause()
    setCurrent(null)
    setPlaying(false)
    setProgress(0)
  }, [projectId])

  function load(rel: string) {
    const a = ref.current
    if (!a) return null
    if (current !== rel) {
      a.src = audioUrl(projectId, rel)
      setCurrent(rel)
      setProgress(0)
    }
    return a
  }

  function toggle(rel: string) {
    const a = load(rel)
    if (!a) return
    if (current === rel && playing) a.pause()
    else void a.play().catch(() => setPlaying(false))
  }

  function seek(rel: string, fraction: number) {
    const a = load(rel)
    if (!a) return
    const go = () => { if (a.duration) a.currentTime = Math.max(0, Math.min(1, fraction)) * a.duration }
    if (a.readyState >= 1) go()
    else a.addEventListener("loadedmetadata", go, { once: true })
    void a.play().catch(() => setPlaying(false))
  }

  function stop() {
    ref.current?.pause()
    setCurrent(null)
    setPlaying(false)
    setProgress(0)
  }

  const element = (
    <audio ref={ref} preload="none" className="hidden"
      onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => { setPlaying(false); setProgress(0) }}
      onTimeUpdate={(e) => { const a = e.currentTarget; setProgress(a.duration ? a.currentTime / a.duration : 0) }} />
  )
  return { current, playing, progress, toggle, seek, stop, element }
}
