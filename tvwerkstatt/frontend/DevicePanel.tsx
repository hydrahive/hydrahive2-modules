import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { TvwDevice } from "./api"
import { looksLikeAddress } from "./deviceLogic"
import { DeviceRow, type DeviceActions } from "./DeviceRow"
import { BOX, BTN_MAIN, INPUT, MUTED } from "./ui"

export type { DeviceActions }

/** Bereich „Fernseher“: Liste mit Prüfstand, hinzufügen (nur wenn eingerichtet), erneut prüfen, entfernen. */
export function DevicePanel({ devices, ready, busy, hasBuild = false, actions }: {
  devices: TvwDevice[]; ready: boolean; busy: boolean; hasBuild?: boolean; actions: DeviceActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  const [name, setName] = useState("")
  const [address, setAddress] = useState("")
  const canAdd = ready && !busy && name.trim().length > 0 && looksLikeAddress(address)

  return (
    <section className={BOX} aria-label={t("devices")}>
      <h2 className="text-sm font-semibold text-[#e8eef8]">{t("devices")}</h2>
      {devices.length === 0 && <p className={MUTED}>{t("no_devices")}</p>}
      {devices.map((d) => <DeviceRow key={d.device_id} d={d} busy={busy} hasBuild={hasBuild} actions={actions} />)}

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
