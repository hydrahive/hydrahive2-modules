import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { errorKey, type LabState } from "./logic"
import { ProbeBoxView } from "./ProbeBox"
import { PROBE_JOBS, type ProbeState } from "./probeLogic"

/** L3 auf der Labor-Seite: Stand der Probe laden (neu nach jedem Probe-Auftrag), Knöpfe, „Probe öffnen“ im neuen Tab.
 * Aufträge laufen über den Zustand des Labors (`s.running`); `onJobStarted` lädt ihn neu. */
export function ProbeSection({ s, onJobStarted }: { s: LabState; onJobStarted: () => void }) {
  const { t } = useTranslation("hydralabor")
  const [p, setP] = useState<ProbeState | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState("")
  const load = useCallback(() => api.getProbe().then(setP).catch((e) => setMsg(errorKey(e))), [])
  const probeRunning = PROBE_JOBS.includes(s.running)
  useEffect(() => { if (!probeRunning) load() }, [probeRunning, s.container_running, load])

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); setMsg("")
    try { await fn() } catch (e) { setMsg(errorKey(e)) } finally { setBusy(false) }
  }
  const job = (a: "build" | "start" | "stop") => act(async () => { await api.probeJob(a); onJobStarted() })
  // Tab sofort öffnen (sonst blockt der Browser das Fenster nach dem await), dann die Adresse mit Ticket setzen.
  const open = () => act(async () => {
    const w = window.open("", "_blank")
    try {
      const { url } = await api.openProbe()
      if (w) { w.opener = null; w.location.href = url } else window.location.href = url
    } catch (e) { w?.close(); throw e }
  })
  if (!p) return msg ? <p role="alert" className="text-sm text-red-300">{t(msg)}</p> : null
  return (
    <>
      <ProbeBoxView p={p} job={s.running} busy={busy} containerRunning={s.container_running}
        onBuild={() => job("build")} onStart={() => job("start")} onStop={() => job("stop")} onOpen={open} />
      {msg && <p role="alert" className="text-sm text-red-300">{t(msg)}</p>}
    </>
  )
}
