import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { deviceLine, errorKey } from "./logic"
import { BOX, MUTED, ROW } from "./ui"

/** Modulseite TV-Werkstatt (nur Admins). E1 Baustein 1: Zustand und Geräteliste. */
export function TvWerkstattPage() {
  const [s, setS] = useState<api.TvwState | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const alive = useRef(true)

  const load = useCallback(() => api.getState()
    .then((r) => { if (alive.current) { setS(r); setMsg(null) } })
    .catch((e) => { if (alive.current) setMsg(errorKey(e)) }), [])
  useEffect(() => { alive.current = true; load(); return () => { alive.current = false } }, [load])

  return <PageView s={s} msg={msg} />
}

/** Reine Ansicht: Zustand rein, Seite raus (getrennt, damit sie ohne Server testbar ist). */
export function PageView({ s, msg }: { s: api.TvwState | null; msg: string | null }) {
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
