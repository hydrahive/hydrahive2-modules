import { Bell, Check, ExternalLink } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ticketsApi } from "./api"
import type { TicketNotification } from "./types"

interface Props { onSelect: (ticketId: string) => void }

function relativeTime(value: string, locale: string) {
  const date = new Date(value).getTime()
  if (Number.isNaN(date)) return "—"
  const diff = date - Date.now()
  const absolute = Math.abs(diff)
  const unit: Intl.RelativeTimeFormatUnit = absolute >= 86_400_000 ? "day" : absolute >= 3_600_000 ? "hour" : "minute"
  const divisor = unit === "day" ? 86_400_000 : unit === "hour" ? 3_600_000 : 60_000
  return new Intl.RelativeTimeFormat(locale.startsWith("de") ? "de" : "en", { numeric: "auto" }).format(Math.round(diff / divisor), unit)
}

export function Notifications({ onSelect }: Props) {
  const { t, i18n } = useTranslation("tickets")
  const [items, setItems] = useState<TicketNotification[]>([])
  const [open, setOpen] = useState(false)

  useEffect(() => { void ticketsApi.notifications().then(setItems).catch(() => setItems([])) }, [])

  async function markRead(item: TicketNotification) {
    await ticketsApi.readNotification(item.id).catch(() => {})
    setItems((current) => current.filter((candidate) => candidate.id !== item.id))
    setOpen(false)
    onSelect(item.ticket_id)
  }

  return (
    <div className="relative">
      <button onClick={() => setOpen((value) => !value)} className={`relative grid h-9 w-9 place-items-center rounded-[7px] border transition-colors ${open ? "border-[#3b83a8] bg-[#163248] text-[#c8f2ff]" : "border-[#253247] text-[#8290a4] hover:border-[#31506c] hover:bg-[#111b29] hover:text-[#e8eef8]"}`} title={t("notifications")}><Bell size={16} />{items.length > 0 && <span className="absolute -right-1 -top-1 grid min-h-4 min-w-4 place-items-center rounded-full border border-[#0d1420] bg-[#f59e0b] px-1 text-[9px] font-bold text-[#17120a]">{items.length > 9 ? "9+" : items.length}</span>}</button>
      {open && <div className="absolute right-0 top-11 z-30 w-[330px] overflow-hidden rounded-[8px] border border-[#2a384c] bg-[#0d1420] shadow-2xl shadow-black/40"><div className="flex items-center justify-between border-b border-[#1f2a3b] px-3 py-3"><div><div className="text-xs font-semibold text-[#e8eef8]">{t("notifications")}</div><div className="mt-0.5 text-[10px] text-[#607188]">{items.length} {t("unread")}</div></div><Bell size={14} className="text-[#69d7ff]" /></div>{items.length === 0 ? <p className="px-3 py-5 text-center text-xs text-[#607188]">{t("noNotifications")}</p> : <div className="max-h-80 overflow-y-auto p-1.5">{items.map((item) => <button key={item.id} onClick={() => void markRead(item)} className="flex w-full items-start gap-2.5 rounded-[6px] px-2.5 py-2.5 text-left transition-colors hover:bg-[#111b29]"><span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[#f59e0b]" /><span className="min-w-0 flex-1"><span className="block text-xs leading-5 text-[#b7c4d3]">{t(`notification.${item.kind}`, { defaultValue: item.kind })}</span><span className="mt-1 block text-[10px] text-[#607188]">{relativeTime(item.created_at, i18n.language)}</span></span><span className="mt-1 flex items-center gap-1 text-[10px] text-[#607188]"><ExternalLink size={11} />{t("open")}</span><Check size={13} className="mt-1 text-[#607188]" /></button>)}</div>}</div>}
    </div>
  )
}
