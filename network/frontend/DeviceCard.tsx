import { useTranslation } from "react-i18next"
import type { Device, Port } from "./admin"
import { bytes, speed, uptime } from "./fmt"
import { BOX, H2, MUTED } from "./ui"

const STATE_DOT: Record<string, string> = { online: "bg-emerald-400", offline: "bg-rose-500", pending: "bg-amber-400" }

function PortCell({ p }: { p: Port }) {
  const { t } = useTranslation("network")
  const tone = !p.up ? "text-[#c8d2df] opacity-60" : p.errors > 0 ? "text-amber-300" : "text-[#e8eef8]"
  return (
    <li className={`rounded border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-1 text-xs ${tone}`}>
      <div className="font-medium">{p.name}{p.uplink && <span className="ml-1 text-sky-300">{t("dev.port_uplink")}</span>}</div>
      <div>{p.up ? speed(p.speed) : t("dev.port_down")}</div>
      {p.up && <div className="text-[#c8d2df]">↓ {bytes(p.tx_bytes)} · ↑ {bytes(p.rx_bytes)}</div>}
      {p.poe && p.poe_w ? <div>{t("dev.poe", { w: p.poe_w })}</div> : null}
      {p.errors > 0 && <div>{t("dev.errors", { n: p.errors })}</div>}
    </li>
  )
}

/** Ein Gerät mit Kopfzeile, Kennzahlen, Anschlüssen und Funk. */
export function DeviceCard({ d }: { d: Device }) {
  const { t } = useTranslation("network")
  return (
    <section className={BOX} data-device={d.kind}>
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className={H2}><span className={`mr-2 inline-block h-2.5 w-2.5 rounded-full ${STATE_DOT[d.state] ?? "bg-[rgb(var(--hh-s-rand,42_54_75))]"}`} aria-hidden />{d.name}</h2>
        <span className="text-xs text-[#c8d2df]">{t(`kind.${d.kind}`)} · {d.model ?? "–"} · {t(`state.${d.state}`)}{d.ip ? ` · ${d.ip}` : ""}</span>
      </header>
      {!d.adopted ? <p className={MUTED}>{t("dev.not_adopted")}</p> : (
        <>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-[#e8eef8]">
            {d.version && <span>{t("dev.firmware", { v: d.version })}</span>}
            {d.upgradable && <span className="text-amber-300">{t("dev.update", { v: d.upgrade_to ?? "" })}</span>}
            <span>{t("dev.uptime", { d: uptime(d.uptime_s, t) })}</span>
            {d.clients !== null && <span>{t("dev.clients", { n: d.clients })}</span>}
            {d.cpu !== null && <span>{t("dev.cpu", { v: d.cpu })}</span>}
            {d.mem !== null && <span>{t("dev.mem", { v: d.mem })}</span>}
            {d.temps.map((x) => <span key={x.name}>{t("dev.temp", { name: x.name, v: x.value })}</span>)}
          </div>
          <p className="text-xs text-[#c8d2df]">{t("dev.traffic", { tx: bytes(d.tx_bytes), rx: bytes(d.rx_bytes) })}</p>
          {d.uplink && <p className="text-xs text-[#c8d2df]">{t("dev.uplink", { name: d.uplink.name ?? d.uplink.mac, port: d.uplink.port ? t("dev.uplink_port", { n: d.uplink.port }) : "" })}</p>}
          {d.ports.length > 0 && <div className="space-y-1">
            <h3 className="text-sm text-[#c8d2df]">{t("dev.ports")}</h3>
            <ul className="grid grid-cols-2 gap-1.5 sm:grid-cols-4 lg:grid-cols-6">{d.ports.map((p) => <PortCell key={p.idx} p={p} />)}</ul>
          </div>}
          {d.radios.length > 0 && <div className="space-y-1">
            <h3 className="text-sm text-[#c8d2df]">{t("dev.radios")}</h3>
            <ul className="grid gap-1.5 sm:grid-cols-2">{d.radios.map((r) => (
              <li key={r.band} className="rounded border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-1 text-xs text-[#e8eef8]">
                <div className="font-medium">{t("dev.band", { b: r.band })} · {t("dev.channel", { c: r.channel ?? "–" })} · {t("dev.power", { p: r.tx_power ?? "–" })}</div>
                <div className="text-[#c8d2df]">{t("dev.clients", { n: r.clients ?? 0 })} · {t("dev.util", { u: r.utilization ?? "–" })} · {t("dev.satisfaction", { s: r.satisfaction ?? "–" })}</div>
              </li>))}</ul>
          </div>}
        </>
      )}
    </section>
  )
}
