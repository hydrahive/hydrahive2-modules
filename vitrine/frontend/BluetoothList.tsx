import { useTranslation } from "react-i18next"
import { Bluetooth, Headphones, Keyboard, Mouse, Smartphone, Speaker, Trash2 } from "lucide-react"
import type { BtDevice, BtView } from "./api"

const ICON = { keyboard: Keyboard, mouse: Mouse, headphones: Headphones, speaker: Speaker, phone: Smartphone, other: Bluetooth }

function Bars({ n, rssi }: { n: number; rssi: number | null }) {
  return (
    <span className="flex shrink-0 items-end gap-0.5" title={rssi !== null ? `${rssi} dBm` : undefined}>
      {[1, 2, 3, 4].map((i) => <span key={i} className={`w-1 rounded-sm ${i <= n ? "bg-[#69d7ff]" : "bg-[#2a364b]"}`} style={{ height: 3 + i * 3 }} />)}
      <span className="ml-1 text-[10px] text-[#718097]">{rssi !== null ? `${rssi} dBm` : ""}</span>
    </span>
  )
}

interface RowProps { d: BtDevice; open: boolean; pairing: string | null; onPair: (a: string) => void; onRemove: (a: string) => void }

function Row({ d, open, pairing, onPair, onRemove }: RowProps) {
  const { t } = useTranslation("vitrine")
  const Icon = ICON[d.kind] ?? Bluetooth
  const addr = d.addresses[0]
  const busy = pairing !== null && d.addresses.includes(pairing)
  const state = d.connected ? t("bt_connected") : d.paired ? t("bt_paired") : t("bt_new")
  return (
    <li className="flex items-center gap-3 px-3 py-2 text-sm text-[#c8d2df]">
      <Icon size={16} className="shrink-0 text-[#69d7ff]" />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-semibold">{d.name}</span>
        <span className="block truncate font-mono text-[10px] text-[#718097]">{d.addresses.join(" · ")}</span>
      </span>
      <Bars n={d.bars} rssi={d.rssi} />
      <span className={`w-20 shrink-0 text-xs ${d.connected ? "text-emerald-300" : "text-[#718097]"}`}>{busy ? t("bt_pairing") : state}</span>
      {d.paired
        ? <button type="button" data-bt-remove={addr} onClick={() => onRemove(addr)} title={t("bt_remove")} aria-label={t("bt_remove")}
            className="shrink-0 rounded-[4px] p-1 text-[#718097] hover:bg-rose-500/20 hover:text-rose-200"><Trash2 size={14} /></button>
        : open && <button type="button" data-bt-pair={addr} disabled={pairing !== null} onClick={() => onPair(addr)}
            className="shrink-0 rounded-[4px] border border-[#69d7ff]/40 bg-[#69d7ff]/10 px-2 py-1 text-xs font-bold text-[#69d7ff] disabled:opacity-50">
            {t("bt_pair")}</button>}
    </li>
  )
}

export interface BluetoothListProps { v: BtView; onScan: () => void; onPair: (a: string) => void; onRemove: (a: string) => void }

/** S7: reine Ansicht der Bluetooth-Karte (Laden und Takt in BluetoothCard). Texte nur als Text, nie als HTML. */
export function BluetoothList({ v, onScan, onPair, onRemove }: BluetoothListProps) {
  const { t } = useTranslation("vitrine")
  if (!v.available) return <p className="rounded-[4px] border border-dashed border-[#2a364b] p-3 text-center text-xs text-[#718097]">{t("bt_unavailable")}</p>
  const open = v.window_left > 0
  const pairing = v.pairing?.address ?? null
  const main = v.devices.filter((d) => d.paired || (open && !d.more))
  const more = open ? v.devices.filter((d) => !d.paired && d.more) : []
  const row = (d: BtDevice) => <Row key={d.addresses[0]} d={d} open={open} pairing={pairing} onPair={onPair} onRemove={onRemove} />
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2 text-xs text-[#718097]">
        <span>{v.adapter ? `${v.adapter.name} · ${v.adapter.powered ? t("bt_on") : t("bt_off")}` : ""}</span>
        <button type="button" data-bt-scan="1" disabled={open} onClick={onScan}
          className="ml-auto flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff]/40 bg-[#69d7ff]/10 px-3 py-1.5 text-xs font-bold text-[#69d7ff] disabled:opacity-60">
          <Bluetooth size={13} />{open ? t("bt_window_left", { s: v.window_left }) : t("bt_scan")}
        </button>
      </div>
      {v.weak_signal && <p className="rounded-[4px] border border-amber-300/40 bg-amber-300/10 p-2 text-xs text-amber-100">{t("bt_weak")}</p>}
      {v.pairing?.passkey && (
        <div className="rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/10 p-3 text-center">
          <p className="font-mono text-4xl font-black tracking-[0.3em] text-[#e8eef8]">{v.pairing.passkey}</p>
          <p className="mt-1 text-xs text-[#c8d2df]">{t("bt_passkey_hint")}</p>
        </div>
      )}
      {v.error && <p className="text-xs text-rose-300">{v.error}</p>}
      {main.length === 0
        ? <p className="rounded-[4px] border border-dashed border-[#2a364b] p-3 text-center text-xs text-[#718097]">{open ? t("bt_searching") : t("bt_none")}</p>
        : <ul className="divide-y divide-[#1c2638] rounded-[4px] border border-[#2a364b] bg-[#111827]">{main.map(row)}</ul>}
      {more.length > 0 && (
        <details className="rounded-[4px] border border-[#2a364b] bg-[#0d1420]">
          <summary className="cursor-pointer px-3 py-2 text-xs text-[#718097]">{t("bt_more", { n: more.length })}</summary>
          <ul className="divide-y divide-[#1c2638]">{more.map(row)}</ul>
        </details>
      )}
    </div>
  )
}
