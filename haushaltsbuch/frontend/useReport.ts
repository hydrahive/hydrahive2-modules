import { useEffect, useState } from "react"

/** Ergebnis eines Abrufs; `undefined` heißt: noch unterwegs (Laden). */
export type ReportResult<T> = { ok: true; data: T } | { ok: false; error: unknown }

/**
 * Lädt einen Report. `load` muss stabil sein (useCallback / Loader-Fabrik) – ein neuer Wert
 * (z. B. anderer Zeitraum) löst genau einen neuen Abruf aus und zeigt bis dahin „Laden“.
 */
export function useReport<T>(load: () => Promise<T>) {
  const [tick, setTick] = useState(0)
  const [done, setDone] = useState<{ load: () => Promise<T>; tick: number; result: ReportResult<T> }>()
  useEffect(() => {
    let alive = true
    load().then(
      (data) => { if (alive) setDone({ load, tick, result: { ok: true, data } }) },
      (error) => { if (alive) setDone({ load, tick, result: { ok: false, error } }) },
    )
    return () => { alive = false }
  }, [load, tick])
  const state = done && done.load === load && done.tick === tick ? done.result : undefined
  return { state, retry: () => setTick((value) => value + 1) }
}
