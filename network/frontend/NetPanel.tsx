import { useState } from "react"
import { useTranslation } from "react-i18next"
import { getNet, type Net, type TreeNode } from "./admin"
import { countNodes } from "./fmt"
import { Stale } from "./Stale"
import { BOX, H2, MUTED } from "./ui"
import { useUdm } from "./useUdm"

/** Ein Knoten im Aufbau. Clients eines Geräts sind zuerst eingeklappt (nur Anzahl). */
export function TreeItem({ n, depth = 0 }: { n: TreeNode; depth?: number }) {
  const { t } = useTranslation("network")
  const [open, setOpen] = useState(false)
  const devices = n.children.filter((c) => c.kind === "device")
  const clients = n.children.filter((c) => c.kind === "client")
  return (
    <li className="space-y-1">
      <div className="text-sm text-[#e8eef8]">
        <span className={n.kind === "device" ? "font-semibold" : ""}>{n.name}</span>
        {n.model && <span className="ml-2 text-xs text-[#c8d2df]">{n.model}</span>}
        {n.link === "wireless" && <span className="ml-2 text-xs text-sky-300">{t("cl.wireless")}</span>}
      </div>
      {(devices.length > 0 || clients.length > 0) && (
        <ul className="ml-3 space-y-1 border-l border-[rgb(var(--hh-s-rand,42_54_75))] pl-3">
          {devices.map((c) => <TreeItem key={c.mac} n={c} depth={depth + 1} />)}
          {clients.length > 0 && <li>
            <button type="button" className="text-xs text-[#c8d2df] underline" onClick={() => setOpen(!open)}>
              {t("net.clients_hidden", { n: clients.length })} – {t(open ? "net.hide" : "net.show")}
            </button>
            {open && <ul className="mt-1 space-y-0.5">{clients.map((c) => <TreeItem key={c.mac} n={c} depth={depth + 1} />)}</ul>}
          </li>}
        </ul>
      )}
    </li>
  )
}

export function NetView({ n }: { n: Net }) {
  const { t } = useTranslation("network")
  const total = n.tree.reduce((s, r) => s + countNodes(r), 0)
  return (
    <div className="space-y-4">
      <section className={BOX}>
        <h2 className={H2}>{t("net.tree")}</h2>
        <p className={MUTED}>{t("net.tree_hint", { n: total })}</p>
        <ul className="space-y-2">{n.tree.map((r) => <TreeItem key={r.mac} n={r} />)}</ul>
      </section>
      <div className="grid gap-4 md:grid-cols-2">
        <section className={BOX}>
          <h2 className={H2}>{t("net.networks")}</h2>
          <ul className="space-y-1 text-sm">{n.networks.map((x) => (
            <li key={x.name} className="text-[#e8eef8]">{x.name} <span className="text-xs text-[#c8d2df]">
              · {t(x.purpose === "wan" ? "net.wan" : "net.lan")}{x.vlan ? ` · ${t("net.vlan", { v: x.vlan })}` : ""}{x.subnet ? ` · ${x.subnet}` : ""}
              {x.dhcp && ` · ${x.dhcp.on ? t("net.dhcp", { start: x.dhcp.start, stop: x.dhcp.stop }) : t("net.dhcp_off")}`}</span></li>))}</ul>
        </section>
        <section className={BOX}>
          <h2 className={H2}>{t("net.wlans")}</h2>
          {n.wlans.length === 0 ? <p className={MUTED}>{t("net.none")}</p> : <ul className="space-y-1 text-sm">{n.wlans.map((w) => (
            <li key={w.name} className="text-[#e8eef8]">{w.name} <span className="text-xs text-[#c8d2df]">
              · {t(w.enabled ? "net.wlan_on" : "net.wlan_off")} · {(w.wpa_mode ?? w.security ?? "").toUpperCase()} · {w.bands.join(" + ")}
              {w.guest ? ` · ${t("net.guest")}` : ""}{w.hidden ? ` · ${t("net.hidden")}` : ""}</span></li>))}</ul>}
        </section>
        <section className={BOX}>
          <h2 className={H2}>{t("net.forwards")}</h2>
          {n.forwards.length === 0 ? <p className={MUTED}>{t("net.none")}</p> : <ul className="space-y-1 text-sm">{n.forwards.map((f) => (
            <li key={`${f.name}-${f.port}`} className={f.enabled ? "text-[#e8eef8]" : "text-[#c8d2df]"}>{f.name}: {t("net.fwd", { port: f.port, proto: f.proto, ip: f.to_ip, to: f.to_port })}{!f.enabled && ` (${t("net.fwd_off")})`}</li>))}</ul>}
          <p className="text-xs text-[#c8d2df]">{t("net.rules", { n: n.firewall_rules, r: n.routes })}</p>
        </section>
      </div>
    </div>
  )
}

export function NetPanel() {
  const { data, err, busy, reload } = useUdm(getNet)
  return (
    <div className="space-y-4" data-network-net>
      <Stale meta={data} err={err} busy={busy} onReload={reload} />
      {data && <NetView n={data} />}
    </div>
  )
}
