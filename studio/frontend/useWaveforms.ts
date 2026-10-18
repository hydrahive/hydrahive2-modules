import { useEffect, useRef, useState } from "react"
import { timelineApi, type TimelineClip } from "./timelineApi"

export const PER_SECOND = 50             // wie auf dem Server (backend/waveform.py PER_SECOND)

/** Wellenformen und echte Länge der Tondateien laden (`lengths`: media_rel → Sekunden) – je Datei einmal, auch wenn sie mehrfach auf der Zeitleiste liegt. Fehler →
 *  leere Liste (flache Linie), nichts bricht. Beim Projektwechsel beginnt der Speicher neu; späte Antworten des
 *  vorigen Projekts werden verworfen. */
export function useWaveforms(projectId: string, clips: TimelineClip[]) {
  const [store, setStore] = useState<{ pid: string; peaks: Record<string, number[]>; lengths: Record<string, number> }>({ pid: projectId, peaks: {}, lengths: {} })
  const asked = useRef<{ pid: string; rels: Set<string> }>({ pid: "", rels: new Set() })
  const rels = [...new Set(clips.filter((c) => c.kind === "audio" && !c.missing && c.media_rel).map((c) => c.media_rel))]
  const key = `${projectId}|${rels.join("|")}`

  useEffect(() => {
    if (asked.current.pid !== projectId) asked.current = { pid: projectId, rels: new Set() }
    const mine = asked.current
    const put = (rel: string, peaks: number[], length = 0) => {
      if (asked.current !== mine) return
      setStore((s) => {
        const same = s.pid === projectId
        return { pid: projectId, peaks: { ...(same ? s.peaks : {}), [rel]: peaks },
          lengths: length > 0 ? { ...(same ? s.lengths : {}), [rel]: length } : same ? s.lengths : {} }
      })
    }
    for (const rel of key.split("|").slice(1)) {
      if (!rel || mine.rels.has(rel)) continue
      mine.rels.add(rel)
      timelineApi.waveform(projectId, rel).then((w) => put(rel, w.peaks, w.duration), () => put(rel, []))
    }
  }, [projectId, key])

  return store.pid === projectId ? store : { peaks: {}, lengths: {} }
}
