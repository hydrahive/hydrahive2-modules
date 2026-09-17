import { Inbox, Plus, Search } from "lucide-react"
import { useTranslation } from "react-i18next"
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

export function TicketList({ tickets, filters, loading, activeId, onFiltersChange, onSelect, onNew }: Props) {
  const { t } = useTranslation("tickets")
  return (
    <aside className="flex min-h-0 w-full flex-col border-r border-white/10 bg-zinc-950/50 lg:w-[25rem]">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
          <Inbox size={17} className="text-sky-400" />{t("inbox")}
        </div>
        <button onClick={onNew} className="rounded-lg bg-sky-500/20 p-2 text-sky-300 hover:bg-sky-500/30" title={t("newTicket")}>
          <Plus size={16} />
        </button>
      </div>
      <div className="space-y-2 border-b border-white/10 p-3">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            value={filters.query ?? ""}
            onChange={(event) => onFiltersChange({ ...filters, query: event.target.value })}
            placeholder={t("search")}
            className="w-full rounded-lg border border-white/10 bg-zinc-900 py-2 pl-9 pr-3 text-sm text-zinc-100 outline-none focus:border-sky-400/50"
          />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <select value={filters.status ?? ""} onChange={(event) => onFiltersChange({ ...filters, status: event.target.value || undefined })} className="rounded-lg border border-white/10 bg-zinc-900 px-2 py-2 text-xs text-zinc-300">
            <option value="">{t("allStatuses")}</option>
            {statuses.map((status) => <option key={status} value={status}>{t(`status.${status}`)}</option>)}
          </select>
          <select value={filters.priority ?? ""} onChange={(event) => onFiltersChange({ ...filters, priority: event.target.value || undefined })} className="rounded-lg border border-white/10 bg-zinc-900 px-2 py-2 text-xs text-zinc-300">
            <option value="">{t("allPriorities")}</option>
            {priorities.map((priority) => <option key={priority} value={priority}>{t(`priority.${priority}`)}</option>)}
          </select>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {loading ? <p className="p-3 text-sm text-zinc-500">{t("loading")}</p> : tickets.length === 0 ? <p className="p-3 text-sm text-zinc-500">{t("empty")}</p> : (
          <div className="space-y-1">
            {tickets.map((ticket) => (
              <button key={ticket.id} onClick={() => onSelect(ticket.id)} className={`w-full rounded-xl border p-3 text-left transition-colors ${activeId === ticket.id ? "border-sky-400/40 bg-sky-500/10" : "border-transparent hover:border-white/10 hover:bg-white/[3%]"}`}>
                <div className="mb-1 flex items-center justify-between gap-2 text-[11px] text-zinc-500"><span>#{ticket.number}</span><span>{t(`status.${ticket.status}`)}</span></div>
                <div className="truncate text-sm font-medium text-zinc-100">{ticket.title}</div>
                <div className="mt-2 flex items-center justify-between text-[11px] text-zinc-500"><span className={`rounded px-1.5 py-0.5 ${ticket.priority === "urgent" ? "bg-red-500/20 text-red-300" : ticket.priority === "high" ? "bg-amber-500/20 text-amber-300" : "bg-white/5"}`}>{t(`priority.${ticket.priority}`)}</span><span>{new Date(ticket.updated_at).toLocaleDateString()}</span></div>
              </button>
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}
