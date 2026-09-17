import { Bell, Check } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ticketsApi } from "./api"
import type { TicketNotification } from "./types"

interface Props { onSelect: (ticketId: string) => void }

export function Notifications({ onSelect }: Props) {
  const { t } = useTranslation("tickets")
  const [items, setItems] = useState<TicketNotification[]>([])
  const [open, setOpen] = useState(false)

  useEffect(() => { void ticketsApi.notifications().then(setItems).catch(() => setItems([])) }, [])

  async function markRead(item: TicketNotification) {
    await ticketsApi.readNotification(item.id).catch(() => {})
    setItems((current) => current.filter((candidate) => candidate.id !== item.id))
    onSelect(item.ticket_id)
  }

  return (
    <div className="relative">
      <button onClick={() => setOpen((value) => !value)} className="relative rounded-lg p-2 text-zinc-400 hover:bg-white/5 hover:text-zinc-100" title={t("notifications")}><Bell size={17} />{items.length > 0 && <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-sky-400" />}</button>
      {open && <div className="absolute right-0 top-11 z-20 w-80 rounded-xl border border-white/10 bg-zinc-900 p-2 shadow-2xl"><div className="px-2 py-2 text-xs font-semibold text-zinc-300">{t("notifications")}</div>{items.length === 0 ? <p className="px-2 py-3 text-xs text-zinc-500">{t("noNotifications")}</p> : items.map((item) => <button key={item.id} onClick={() => void markRead(item)} className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-xs text-zinc-300 hover:bg-white/5"><span className="min-w-0 flex-1">{t(`notification.${item.kind}`, { defaultValue: item.kind })}</span><Check size={13} className="text-emerald-400" /></button>)}</div>}
    </div>
  )
}
