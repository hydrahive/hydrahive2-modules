import { useState } from "react"
import { useTranslation } from "react-i18next"
import { getClients, type Client, type ClientFilter } from "./admin"
import { bytes, signalLevel, uptime } from "./fmt"
import { Stale } from "./Stale"
import { BOX, INPUT, MUTED } from "./ui"
import { useUdm } from "./useUdm"
import { when } from "./when"

const SIG: Record<string, string> = { good: "text-emerald-300", ok: "text-[#e8eef8]", weak: "text-amber-300", bad: "text-rose-300" }

/** Eine Zeile je Client (auch auf dem Handy lesbar: umbrechend statt Tabelle). */
export function ClientRow({ c }: { c: Client }) {
  const { t, i18n } = useTranslation("network")
  const lvl = signalLevel(c.signal)
  const via = c.wired
    ? t("cl.via_wire", { dev: c.uplink_name ?? t("cl.unknown_uplink"), port: c.uplink_port ? t("cl.port", { n: c.uplink_port }) : "" })
    : t("cl.via_wlan", { band: c.band ?? "?", ap: c.uplink_name ?? t("cl.unknown_uplink") })
  return (
    <li className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 py-2" data-client={c.online ? "online" : "offline"}>
      <span className={`h-2 w-2 shrink-0 self-center rounded-full ${c.online ? "bg-emerald-400" : "bg-[rgb(var(--hh-s-rand,42_54_75))]"}`} aria-hidden />
      <span className="min-w-0 basis-full break-words font-medium text-[#e8eef8] sm:basis-56">{c.name}</span>
      <span className="text-xs text-[#c8d2df]">{c.vendor ?? ""}{c.ip ? ` · ${c.ip}` : ""}</span>
      <span className="text-xs text-[#c8d2df]">{via}</span>
      {lvl && c.online && <span className={`text-xs ${SIG[lvl]}`}>{t("cl.signal", { s: c.signal })} ({t(`sig.${lvl}`)})</span>}
      {c.online ? <>
        <span className="text-xs text-[#c8d2df]">{uptime(c.uptime_s, t)}</span>
        <span className="text-xs text-[#e8eef8]">{t("cl.down", { v: bytes(c.down_bytes) })} · {t("cl.up", { v: bytes(c.up_bytes) })}</span>
      </> : <span className="text-xs text-[#c8d2df]">{t("cl.last_seen", { when: when(c.last_seen, i18n.language) })}</span>}
      {c.guest && <span className="text-xs text-amber-300">{t("cl.guest")}</span>}
      {c.fixed_ip && <span className="text-xs text-sky-300">{t("cl.fixed_ip")}</span>}
    </li>
  )
}

function Seg<T extends string>({ value, options, onChange }: { value: T; options: [T, string][]; onChange: (v: T) => void }) {
  return (
    <div className="flex overflow-hidden rounded border border-[rgb(var(--hh-s-rand,42_54_75))]" role="group">
      {options.map(([v, label]) => (
        <button key={v} type="button" aria-pressed={value === v} onClick={() => onChange(v)}
          className={`px-2.5 py-1.5 text-sm ${value === v ? "bg-[rgb(var(--hh-s-hebung,27_37_54))] text-[#e8eef8]" : "text-[#c8d2df]"}`}>{label}</button>
      ))}
    </div>
  )
}

export function ClientsPanel() {
  const { t } = useTranslation("network")
  const [f, setF] = useState<ClientFilter>({ status: "online", link: "all", q: "" })
  const { data, err, busy, reload } = useUdm(() => getClients(f), `${f.status}|${f.link}|${f.q}`)
  return (
    <div className="space-y-3" data-network-clients>
      <Stale meta={data} err={err} busy={busy} onReload={reload} />
      <div className="flex flex-wrap items-center gap-2">
        <input value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} placeholder={t("cl.search")} className={`${INPUT} sm:w-72`} maxLength={100} />
        <Seg value={f.status} onChange={(status) => setF({ ...f, status })} options={[["online", t("cl.online")], ["offline", t("cl.offline")], ["all", t("cl.all")]]} />
        <Seg value={f.link} onChange={(link) => setF({ ...f, link })} options={[["all", t("cl.all")], ["wireless", t("cl.wireless")], ["wired", t("cl.wired")]]} />
      </div>
      {data && <p className={MUTED}>{t("cl.counts", { online: data.online, wireless: data.wireless, total: data.total })}</p>}
      {data && (data.items.length === 0 ? <p className={MUTED}>{t("cl.none")}</p> : (
        <ul className={`${BOX} divide-y divide-[rgb(var(--hh-s-rand,42_54_75))]`}>{data.items.map((c) => <ClientRow key={c.mac} c={c} />)}</ul>
      ))}
    </div>
  )
}
