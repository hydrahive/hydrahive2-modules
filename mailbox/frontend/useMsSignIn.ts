import { useCallback, useEffect, useRef, useState } from "react"
import { mailApi } from "./api"
import { errorCode, nextState, pollDelayMs, startErrorKey, type FlowStart, type FlowState } from "./msFlow"

/** Microsoft-Anmeldung per Geräte-Code: starten → Code zeigen → im Takt nachfragen → flow_id für das Konto. */
export function useMsSignIn() {
  const [state, setState] = useState<FlowState>("idle")
  const [flow, setFlow] = useState<FlowStart | null>(null)
  const [errKey, setErrKey] = useState<string | null>(null)
  const [detail, setDetail] = useState("")
  const timer = useRef<number | null>(null)
  const alive = useRef(true)

  const stop = useCallback(() => {
    if (timer.current !== null) window.clearTimeout(timer.current)
    timer.current = null
  }, [])

  useEffect(() => {
    alive.current = true
    return () => { alive.current = false; stop() }
  }, [stop])

  const poll = useCallback((f: FlowStart) => {
    timer.current = window.setTimeout(async () => {
      try {
        const r = await mailApi.msPoll(f.flow_id)
        if (!alive.current) return
        const s = nextState(r)
        setState(s)
        if (s === "error") setDetail(r.error ?? "")
        if (s === "waiting") poll(f)
      } catch {
        if (!alive.current) return
        poll(f)                       // kurzer Netzaussetzer: weiter warten, Microsoft-Ablauf beendet es sonst
      }
    }, pollDelayMs(f.interval))
  }, [])

  const start = useCallback(async () => {
    stop()
    setState("starting"); setErrKey(null); setDetail(""); setFlow(null)
    try {
      const f = await mailApi.msStart()
      if (!alive.current) return
      setFlow(f); setState("waiting")
      poll(f)
    } catch (e) {
      if (!alive.current) return
      setErrKey(startErrorKey(errorCode(e))); setDetail(e instanceof Error ? e.message : ""); setState("error")
    }
  }, [poll, stop])

  const reset = useCallback(() => { stop(); setState("idle"); setFlow(null); setErrKey(null); setDetail("") }, [stop])

  return { state, flow, errKey, detail, start, reset }
}
