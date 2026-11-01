import { useTranslation } from "react-i18next"
import { getTraffic, type Traffic } from "./admin"
import { bytes, share } from "./fmt"
import { Stale } from "./Stale"
import { BOX, H2, MUTED } from "./ui"
import { useUdm } from "./useUdm"

export function TrafficView({ d }: { d: Traffic }) {
  const { t } = useTranslation("network")
  const max = Math.max(0, ...d.clients.map((c) => (c.down_bytes ?? 0) + (c.up_bytes ?? 0)))
  return (
    <div className="space-y-4">
      <section className={BOX}>
        <h2 className={H2}>{t("tr.clients")}</h2>
        {d.clients.length === 0 ? <p className={MUTED}>{t("tr.none")}</p> : <ul className="space-y-2">{d.clients.map((c) => {
          const total = (c.down_bytes ?? 0) + (c.up_bytes ?? 0)
          return (
            <li key={c.mac} className="space-y-0.5">
              <div className="flex flex-wrap justify-between gap-x-3 text-sm"><span className="break-words text-[#e8eef8]">{c.name}</span>
                <span className="text-xs text-[#c8d2df]">{t("cl.down", { v: bytes(c.down_bytes) })} · {t("cl.up", { v: bytes(c.up_bytes) })}</span></div>
              <div className="h-1.5 rounded bg-[rgb(var(--hh-s-hebung,27_37_54))]"><div className="h-1.5 rounded bg-sky-400" style={{ width: `${share(total, max)}%` }} /></div>
            </li>)
        })}</ul>}
      </section>
      <section className={BOX}>
        <h2 className={H2}>{t("tr.devices")}</h2>
        {d.devices.map((dev) => (
          <div key={dev.name} className="space-y-1">
            <div className="text-sm text-[#e8eef8]">{dev.name} <span className="text-xs text-[#c8d2df]">· {t("dev.traffic", { tx: bytes(dev.tx_bytes), rx: bytes(dev.rx_bytes) })}</span></div>
            {dev.ports.length > 0 && <ul className="grid grid-cols-2 gap-1 text-xs sm:grid-cols-4">{dev.ports.filter((p) => p.up).map((p) => (
              <li key={p.idx} className="text-[#c8d2df]">{p.name}: ↓ {bytes(p.tx_bytes)} · ↑ {bytes(p.rx_bytes)}</li>))}</ul>}
          </div>))}
      </section>
    </div>
  )
}

export function TrafficPanel() {
  const { data, err, busy, reload } = useUdm(getTraffic)
  return (
    <div className="space-y-4" data-network-traffic>
      <Stale meta={data} err={err} busy={busy} onReload={reload} />
      {data && <TrafficView d={data} />}
    </div>
  )
}
