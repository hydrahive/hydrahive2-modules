import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { deviceLine, errorKey } from "./logic"
import { SetupPanel, type SetupActions } from "./SetupPanel"
import { pollMs, setupView } from "./setupLogic"
import { BOX, MUTED, ROW } from "./ui"

/** Modulseite TV-Werkstatt (nur Admins). E1 Baustein 3: Bauumgebung einrichten, Geräteliste. */
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

  const ms = s ? pollMs(setupView(s.setup, s.container)) : null
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

  const actions: SetupActions = {
    onSetup: (accept) => act(() => api.startSetup(accept)),
    onStop: () => act(api.stopContainer),
    onRemove: () => { if (window.confirm(t("setup.remove_confirm"))) act(api.removeContainer) },
  }
  return <PageView s={s} msg={msg} busy={busy} actions={actions} />
}

const NOOP: SetupActions = { onSetup: () => {}, onStop: () => {}, onRemove: () => {} }

/** Reine Ansicht: Zustand rein, Seite raus (getrennt, damit sie ohne Server testbar ist). */
export function PageView({ s, msg, busy = false, actions = NOOP }: {
  s: api.TvwState | null; msg: string | null; busy?: boolean; actions?: SetupActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold text-[#e8eef8]">{t("title")}</h1>
        <p className={MUTED}>{t("subtitle")}</p>
      </header>
      {msg && <p className="text-sm text-red-300" role="alert">{t(msg)}</p>}
      {!s && !msg && <p className={MUTED}>…</p>}
      {s && !s.incus && <p className="text-sm text-amber-200">{t(errorKey(s.error_code))}</p>}
      {s?.incus && <SetupPanel job={s.setup} container={s.container} busy={busy} actions={actions} />}
      {s?.incus && (
        <section className={BOX}>
          <h2 className="text-sm font-semibold text-[#e8eef8]">{t("devices")}</h2>
          {s.devices.length === 0 && <p className={MUTED}>{t("no_devices")}</p>}
          {s.devices.map((d) => (
            <div key={d.device_id} className={ROW}>
              <div className="min-w-0">
                <div className="truncate text-sm text-[#e8eef8]">{d.name}</div>
                <div className="truncate text-xs text-[#9aa7bc]">{deviceLine(d)}</div>
              </div>
              <div className="shrink-0 text-right text-xs text-[#9aa7bc]">
                <div>{d.address}</div>
                <div>{t(`adb.${d.adb_state ?? "unknown"}`)}</div>
              </div>
            </div>
          ))}
        </section>
      )}
    </div>
  )
}
