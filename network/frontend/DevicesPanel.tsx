import { useTranslation } from "react-i18next"
import { getDevices } from "./admin"
import { DeviceCard } from "./DeviceCard"
import { Stale } from "./Stale"
import { MUTED } from "./ui"
import { useUdm } from "./useUdm"

export function DevicesPanel() {
  const { t } = useTranslation("network")
  const { data, err, busy, reload } = useUdm(getDevices)
  return (
    <div className="space-y-4" data-network-devices>
      <Stale meta={data} err={err} busy={busy} onReload={reload} />
      {data && (data.items.length === 0 ? <p className={MUTED}>{t("dev.none")}</p> : data.items.map((d) => <DeviceCard key={d.mac} d={d} />))}
    </div>
  )
}
