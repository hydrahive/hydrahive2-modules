import { useCallback, useEffect, useRef, useState } from "react"
import * as api from "./api"
import { anyChecking } from "./deviceLogic"
import { errorKey } from "./logic"
import { pollMs, setupView } from "./setupLogic"

/** Zustand der Seite: Gesamtzustand, gewähltes Gerät, Desktop des Geräts mit Entwurf des Aussehens, Nachladen. */
export function useWorkshop() {
  const [s, setS] = useState<api.TvwState | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [deviceId, setDeviceId] = useState<string | null>(null)
  const [desk, setDesk] = useState<api.TvwDesktop | null>(null)
  const [draft, setDraft] = useState<api.TvwLook | null>(null)
  const alive = useRef(true)
  const dirtyRef = useRef(false)

  const loadDesk = useCallback((id: string) => api.getDesktop(id)
    .then((d) => { if (!alive.current) return; setDesk(d); if (!dirtyRef.current) setDraft(d.look) })
    .catch((e) => { if (alive.current) setMsg(errorKey(e)) }), [])

  const load = useCallback(() => api.getState()
    .then((r) => {
      if (!alive.current) return
      setS(r); setMsg(null)
      setDeviceId((cur) => (cur && r.devices.some((d) => d.device_id === cur) ? cur : r.devices[0]?.device_id ?? null))
    })
    .catch((e) => { if (alive.current) setMsg(errorKey(e)) }), [])

  useEffect(() => { alive.current = true; load(); return () => { alive.current = false } }, [load])
  useEffect(() => { if (deviceId) { dirtyRef.current = false; loadDesk(deviceId) } }, [deviceId, loadDesk])
  const deskFor = desk && deviceId ? desk : null

  const deskRunning = !!deskFor && [deskFor.read_job, deskFor.push_job].some((j) => j?.state === "running")
  const running = !!s && (anyChecking(s.devices) || s.build?.state === "running" || deskRunning)
  const ms = s ? pollMs(setupView(s.setup, s.container), running) : null
  useEffect(() => {
    if (ms === null) return
    const id = setTimeout(() => { load(); if (deviceId) loadDesk(deviceId) }, ms)
    return () => clearTimeout(id)
  }, [ms, s, desk, load, loadDesk, deviceId])

  const act = useCallback((fn: () => Promise<unknown>, after?: () => void) => {
    setBusy(true)
    fn().then(() => { after?.(); load(); if (deviceId) loadDesk(deviceId) })
      .catch((e) => { if (alive.current) setMsg(errorKey(e)) })
      .finally(() => { if (alive.current) setBusy(false) })
  }, [load, loadDesk, deviceId])

  const editDraft = useCallback((l: api.TvwLook) => {
    setDraft(l)
    dirtyRef.current = !!desk && JSON.stringify(l) !== JSON.stringify(desk.look)
  }, [desk])

  return { s, msg, busy: busy || running, deviceId, setDeviceId, desk: deskFor, draft, editDraft, act, load,
    clearDirty: () => { dirtyRef.current = false } }
}
