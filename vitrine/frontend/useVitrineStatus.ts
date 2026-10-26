import { useEffect, useState } from "react"
import { vitrineApi, type VitrineStatus } from "./api"
import type { LightStatus } from "./light"

const POLL_MS = 5000

/** Display- und Licht-Stand, alle 5 s – einmal für die ganze Seite (Kopf und Reiter teilen ihn). */
export function useVitrineStatus() {
  const [st, setSt] = useState<VitrineStatus | null>(null)
  const [light, setLight] = useState<LightStatus | null>(null)
  const [tick, setTick] = useState(() => Date.now())

  useEffect(() => {
    let alive = true
    const load = () => {
      vitrineApi.status().then((s) => { if (alive) setSt(s) }).catch(() => {})
      vitrineApi.light().then((l) => { if (alive) setLight(l) }).catch(() => {})
      setTick(Date.now())
    }
    load()
    const id = window.setInterval(load, POLL_MS)
    return () => { alive = false; window.clearInterval(id) }
  }, [])

  return { st, light, tick }
}
