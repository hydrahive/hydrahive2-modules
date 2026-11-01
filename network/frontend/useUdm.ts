import { useCallback, useEffect, useRef, useState } from "react"
import type { Meta } from "./admin"
import { errorKey } from "./logic"

/** Lädt Daten der Dream Machine beim Öffnen und wenn sich `key` ändert; reload() holt neu. Fehler als Übersetzungsschlüssel. */
export function useUdm<T extends Meta>(load: () => Promise<T>, key = "") {
  const loader = useRef(load)
  useEffect(() => { loader.current = load })
  const [data, setData] = useState<T | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(true)
  const [tick, setTick] = useState(0)
  useEffect(() => {
    let alive = true
    loader.current()
      .then((d) => { if (alive) { setData(d); setErr(null) } })
      .catch((e) => { if (alive) setErr(errorKey(e)) })
      .finally(() => { if (alive) setBusy(false) })
    return () => { alive = false }
  }, [key, tick])
  const reload = useCallback(() => { setBusy(true); setTick((n) => n + 1) }, [])
  return { data, err, busy, reload }
}
