import { useEffect, useState } from "react"
import { planApi } from "./planApi"

/** Stimmen des Sprachmodells des Drehbuchs (5c). Lädt nur, wenn `active`; je Projekt und Modell einmal. `null` = lädt
 *  noch; Fehler → leer (dann gilt die Standardstimme des Modells). */
export function useVoices(projectId: string, model: string, active: boolean): string[] | null {
  const [got, setGot] = useState<{ key: string; voices: string[] }>({ key: "", voices: [] })
  const key = `${projectId}|${model}`
  useEffect(() => {
    if (!active || !projectId || got.key === key) return
    let alive = true
    planApi.voices(projectId).then((r) => { if (alive) setGot({ key, voices: r.voices }) }, () => { if (alive) setGot({ key, voices: [] }) })
    return () => { alive = false }
  }, [active, projectId, key, got.key])
  return got.key === key ? got.voices : null                           // null = lädt noch
}
