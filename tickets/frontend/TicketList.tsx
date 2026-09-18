import { Inbox, Plus, Search, SlidersHorizontal } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Input, Select } from "@/shared/ui"
import type { Ticket, TicketPriority, TicketStatus } from "./types"
import type { TicketFilters } from "./api"

interface Props {
  tickets: Ticket[]
  filters: TicketFilters
  loading: boolean
  activeId: string | null
  onFiltersChange: (filters: TicketFilters) => void
  onSelect: (id: string) => void
  onNew: () => void
}

const statuses: TicketStatus[] = ["open", "triaged", "in_progress", "waiting", "resolved", "closed", "cancelled"]
const priorities: TicketPriority[] = ["low", "normal", "high", "urgent"]

const priorityDot: Record<TicketPriority, string> = {
  low: "bg-zinc-500",
  normal: "bg-sky-400",
  high: "bg-amber-400",
  urgent: "bg-orange-400",
}

const statusBadge: Record<TicketStatus, string> = {
  open: "border-sky-400/25 bg-sky-400/10 text-sky-200",
  triaged: "border-cyan-400/25 bg-cyan-400/10 text-cyan-200",
  in_progress: "border-violet-400/25 bg-violet-400/10 text-violet-200",
  waiting: "border-amber-400/25 bg-amber-400/10 text-amber-200",
  resolved: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
  closed: "border-zinc-500/25 bg-zinc-500/10 text-zinc-300",
  cancelled: "border-orange-400/25 bg-orange-400/10 text-orange-200",
}

function relativeTime(value: string, locale: string) {
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) return "—"

  const diff = timestamp - Date.now()
  const absolute = Math.abs(diff)
  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["day", 86_400_000],
    ["hour", 3_600_000],
    ["minute", 60_000],
  ]
  const formatter = new Intl.RelativeTimeFormat(locale.startsWith("de") ? "de" : "en", { numeric: "auto" })
  for (const [unit, milliseconds] of units) {
    if (absolute >= milliseconds || unit === "minute") return formatter.format(Math.round(diff / milliseconds), unit)
  }
  return formatter.format(0, "minute")
}

function initials(value: string) {
  const parts = value.split(/[\s._-]+/).filter(Boolean)
  return (parts.length > 1 ? `${parts[0][0]}${parts[1][0]}` : value.slice(0, 2)).toUpperCase()
}

export function TicketList({ tickets, filters, loading, activeId, onFiltersChange, onSelect, onNew }: Props) {
  const { t, i18n } = useTranslation("tickets")
  return (
    <aside className="flex min-h-0 w-full flex-1 flex-col border-r border-[#1f2a3b] bg-[#0c131e] lg:w-[292px] lg:flex-none">
      <div className="border-b border-[#1f2a3b] px-4 pb-3 pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="grid h-7 w-7 place-items-center rounded-[7px] border border-[#2b4058] bg-[#132235] text-[#69d7ff]"><Inbox size={15} /></span>
            <div>
              <div className="text-sm font-semibold text-[#e8eef8]">{t("inbox")}</div>
              <div className="text-[11px] text-[#718096]">{tickets.length} {t("ticketsCount")}</div>
            </div>
          </div>
          <button onClick={onNew} className="grid h-7 w-7 place-items-center rounded-[6px] border border-[#2b4058] text-[#8fa1b8] transition-colors hover:border-[#69d7ff]/60 hover:bg-[#163248] hover:text-[#c8f2ff]" title={t("newTicket")}>
            <Plus size={15} />
          </button>
        </div>
      </div>

      <div className="space-y-2.5 border-b border-[#1f2a3b] px-3 py-3">
        <Input
          value={filters.query ?? ""}
          onChange={(event) => onFiltersChange({ ...filters, query: event.target.value })}
          placeholder={t("search")}
          icon={<Search size={15} />}
          className="border-[#253247] bg-[#111b29] text-xs"
        />
        <div className="flex items-center gap-2">
          <SlidersHorizontal size={14} className="shrink-0 text-[#607188]" />
          <Select value={filters.status ?? ""} onChange={(event) => onFiltersChange({ ...filters, status: event.target.value || undefined })} className="border-[#253247] bg-[#111b29] text-xs">
            <option value="">{t("allStatuses")}</option>
            {statuses.map((status) => <option key={status} value={status}>{t(`status.${status}`)}</option>)}
          </Select>
          <Select value={filters.priority ?? ""} onChange={(event) => onFiltersChange({ ...filters, priority: event.target.value || undefined })} className="border-[#253247] bg-[#111b29] text-xs">
            <option value="">{t("allPriorities")}</option>
            {priorities.map((priority) => <option key={priority} value={priority}>{t(`priority.${priority}`)}</option>)}
          </Select>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
        {loading ? <div className="space-y-2 p-1">{[1, 2, 3, 4].map((item) => <div key={item} className="h-[76px] animate-pulse rounded-[8px] bg-[#111b29]" />)}</div> : tickets.length === 0 ? (
          <div className="flex h-full min-h-[180px] flex-col items-center justify-center px-5 text-center">
            <div className="mb-3 grid h-9 w-9 place-items-center rounded-[8px] border border-[#253247] bg-[#111b29] text-[#607188]"><Inbox size={17} /></div>
            <p className="text-xs font-medium text-[#a9b5c6]">{t("empty")}</p>
            <p className="mt-1 text-[11px] leading-relaxed text-[#607188]">{t("emptyHint")}</p>
          </div>
        ) : (
          <div className="space-y-1">
            {tickets.map((ticket) => (
              <button key={ticket.id} onClick={() => onSelect(ticket.id)} className={`group w-full border px-3 py-3 text-left transition-colors ${activeId === ticket.id ? "border-[#32718e] bg-[#12283a]" : "border-transparent hover:border-[#253247] hover:bg-[#111b29]"}`} style={{ borderRadius: 8 }}>
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <span className="font-mono text-[11px] font-semibold text-[#69d7ff]">#{ticket.number}</span>
                  <span className="text-[10px] text-[#718096]">{relativeTime(ticket.updated_at, i18n.language)}</span>
                </div>
                <div className="truncate text-[13px] font-semibold text-[#e8eef8]">{ticket.title}</div>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <span className="flex min-w-0 items-center gap-1.5 text-[11px] text-[#8290a4]"><span className="grid h-4 w-4 shrink-0 place-items-center rounded-full bg-[#1d2d42] text-[8px] font-semibold text-[#9aaac0]">{initials(ticket.created_by)}</span><span className="truncate">{ticket.created_by}</span></span>
                  <span className="flex shrink-0 items-center gap-1.5 text-[10px] text-[#9aa6b8]"><span className={`h-1.5 w-1.5 rounded-full ${priorityDot[ticket.priority]}`} />{t(`priority.${ticket.priority}`)}</span>
                </div>
                <div className="mt-2 flex items-center gap-1.5 text-[10px] text-[#607188]"><span className={`rounded-[4px] border px-1.5 py-0.5 ${statusBadge[ticket.status]}`}>{t(`status.${ticket.status}`)}</span>{ticket.category && <span className="truncate">· {ticket.category}</span>}</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}
