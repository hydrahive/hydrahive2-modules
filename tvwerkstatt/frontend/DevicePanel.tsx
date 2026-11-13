import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { TvwDevice } from "./api"
import { checkView, kindKey, looksLikeAddress, ourHome } from "./deviceLogic"
import { deviceLine, errorKey } from "./logic"
import { BOX, BTN, BTN_DANGER, BTN_MAIN, INPUT, MUTED, ROW } from "./ui"

export interface DeviceActions {
  onAdd: (name: string, address: string) => void
  onCheck: (id: string) => void
  onRemove: (id: string) => void
}

/** Bereich „Fernseher“: Liste mit Prüfstand, hinzufügen (nur wenn eingerichtet), erneut prüfen, entfernen. */
export function DevicePanel({ devices, ready, busy, actions }: {
  devices: TvwDevice[]; ready: boolean; busy: boolean; actions: DeviceActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  const [name, setName] = useState("")
  const [address, setAddress] = useState("")
  const canAdd = ready && !busy && name.trim().length > 0 && looksLikeAddress(address)

  return (
    <section className={BOX} aria-label={t("devices")}>
      <h2 className="text-sm font-semibold text-[#e8eef8]">{t("devices")}</h2>
      {devices.length === 0 && <p className={MUTED}>{t("no_devices")}</p>}
      {devices.map((d) => <DeviceRow key={d.device_id} d={d} busy={busy} actions={actions} />)}

      {!ready && <p className={MUTED}>{t("device.need_setup")}</p>}
      {ready && (
        <form className="space-y-2" onSubmit={(e) => { e.preventDefault(); if (canAdd) actions.onAdd(name, address) }}>
          <h3 className="text-sm text-[#e8eef8]">{t("device.add_title")}</h3>
          <p className={MUTED}>{t("device.add_explain")}</p>
          <div className="grid gap-2 sm:grid-cols-2">
            <input className={INPUT} value={name} maxLength={60} placeholder={t("device.name_ph")}
              aria-label={t("device.name")} onChange={(e) => setName(e.target.value)} />
            <input className={INPUT} value={address} maxLength={15} placeholder="192.168.178.200" inputMode="decimal"
              aria-label={t("device.address")} onChange={(e) => setAddress(e.target.value)} />
          </div>
          <button type="submit" className={BTN_MAIN} disabled={!canAdd}>{t("device.add")}</button>
        </form>
      )}
    </section>
  )
}

function DeviceRow({ d, busy, actions }: { d: TvwDevice; busy: boolean; actions: DeviceActions }) {
  const { t } = useTranslation("tvwerkstatt")
  const view = checkView(d)
  const kind = kindKey(d.kind)
  return (
    <div className={`${ROW} flex-col items-stretch`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm text-[#e8eef8]">{d.name}</div>
          <div className="truncate text-xs text-[#9aa7bc]">
            {[deviceLine(d), kind ? t(kind) : ""].filter(Boolean).join(" · ")}
          </div>
          {ourHome(d) && <div className="text-xs text-[#69d7ff]">{t("device.our_home")}</div>}
        </div>
        <div className="shrink-0 text-right text-xs text-[#9aa7bc]">
          <div>{d.address}</div>
          <div>{t(`adb.${d.adb_state ?? "unknown"}`)}</div>
        </div>
      </div>
      {view === "checking" && <p className="text-xs text-[#69d7ff]" role="status">{t("device.checking")}</p>}
      {view === "authorize" && (
        <p className="rounded bg-amber-500/10 p-2 text-sm text-amber-200" role="status">{t("device.authorize")}</p>
      )}
      {view === "failed" && d.check && (
        <p className="text-xs text-red-300" role="alert">{t(errorKey(d.check.error_code))}</p>
      )}
      {view !== "checking" && view !== "authorize" && (
        <div className="flex flex-wrap gap-2">
          <button type="button" className={BTN} disabled={busy} onClick={() => actions.onCheck(d.device_id)}>
            {t("device.check")}
          </button>
          <button type="button" className={BTN_DANGER} disabled={busy} onClick={() => actions.onRemove(d.device_id)}>
            {t("device.remove")}
          </button>
        </div>
      )}
    </div>
  )
}
