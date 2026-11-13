import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { DevicePanel, type DeviceActions } from "./DevicePanel"
import { anyChecking } from "./deviceLogic"
import { errorKey } from "./logic"
import { SetupPanel, type SetupActions } from "./SetupPanel"
import { pollMs, setupView } from "./setupLogic"
import { MUTED } from "./ui"

/** Modulseite TV-Werkstatt (nur Admins). E1 Bausteine 3 und 5: Bauumgebung einrichten, Fernseher eintragen und prüfen. */
export function TvWerkstattPage() {
  const { t } = useTranslation("tvwerkstatt")
  const [s, setS] = useState<api.TvwState | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const alive = useRef(true)

  const load = useCallback(() => api.getState()
    .then((r) => { if (alive.current) { setS(r); setMsg(null) } })
    .catch((e) => { if (alive.current) setMsg(errorKey(e)) }), [])
  useEffect(() => { alive.current = true; load(); return () => { alive.current = false } }, [load])

  const ms = s ? pollMs(setupView(s.setup, s.container), anyChecking(s.devices)) : null
  useEffect(() => {
    if (ms === null) return
    const id = setTimeout(load, ms)
    return () => clearTimeout(id)
  }, [ms, s, load])

  const act = useCallback((fn: () => Promise<unknown>) => {
    setBusy(true)
    fn().then(load).catch((e) => { if (alive.current) setMsg(errorKey(e)) })
      .finally(() => { if (alive.current) setBusy(false) })
  }, [load])

  const setup: SetupActions = {
    onSetup: (accept) => act(() => api.startSetup(accept)),
    onStop: () => act(api.stopContainer),
    onRemove: () => { if (window.confirm(t("setup.remove_confirm"))) act(api.removeContainer) },
  }
  const devices: DeviceActions = {
    onAdd: (name, address) => act(() => api.addDevice(name.trim(), address.trim())),
    onCheck: (id) => act(() => api.checkDevice(id)),
    onRemove: (id) => { if (window.confirm(t("device.remove_confirm"))) act(() => api.removeDevice(id)) },
  }
  return <PageView s={s} msg={msg} busy={busy} setup={setup} devices={devices} />
}

const NOOP_SETUP: SetupActions = { onSetup: () => {}, onStop: () => {}, onRemove: () => {} }
const NOOP_DEVICES: DeviceActions = { onAdd: () => {}, onCheck: () => {}, onRemove: () => {} }

/** Reine Ansicht: Zustand rein, Seite raus (getrennt, damit sie ohne Server testbar ist). */
export function PageView({ s, msg, busy = false, setup = NOOP_SETUP, devices = NOOP_DEVICES }: {
  s: api.TvwState | null; msg: string | null; busy?: boolean; setup?: SetupActions; devices?: DeviceActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  const ready = !!s && s.container !== "missing" && setupView(s.setup, s.container) !== "running"
  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold text-[#e8eef8]">{t("title")}</h1>
        <p className={MUTED}>{t("subtitle")}</p>
      </header>
      {msg && <p className="text-sm text-red-300" role="alert">{t(msg)}</p>}
      {!s && !msg && <p className={MUTED}>…</p>}
      {s && !s.incus && <p className="text-sm text-amber-200">{t(errorKey(s.error_code))}</p>}
      {s?.incus && <SetupPanel job={s.setup} container={s.container} busy={busy} actions={setup} />}
      {s?.incus && <DevicePanel devices={s.devices} ready={ready} busy={busy || anyChecking(s.devices)}
        actions={devices} />}
    </div>
  )
}
