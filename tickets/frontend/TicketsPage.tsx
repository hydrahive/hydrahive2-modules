import { useCallback, useEffect, useState } from "react"
import { Plus, Ticket as TicketIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import { ticketsApi, type TicketFilters } from "./api"
import { Notifications } from "./Notifications"
import { TeamSettings } from "./TeamSettings"
import { TicketDetail } from "./TicketDetail"
import { TicketForm } from "./TicketForm"
import { TicketList } from "./TicketList"
import type { Team, Ticket } from "./types"

export function TicketsPage() {
  const { t } = useTranslation("tickets")
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [teams, setTeams] = useState<Team[]>([])
  const [active, setActive] = useState<Ticket | null>(null)
  const [filters, setFilters] = useState<TicketFilters>({})
  const [creating, setCreating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    try { setTickets(await ticketsApi.list(filters)); setError(false) } catch { setError(true) } finally { setLoading(false) }
  }, [filters])
  const reloadTeams = useCallback(() => { void ticketsApi.teams().then(setTeams).catch(() => setTeams([])) }, [])

  useEffect(() => { void reload() }, [reload])
  useEffect(() => { reloadTeams() }, [reloadTeams])

  async function selectTicket(id: string) {
    setCreating(false)
    try { setActive(await ticketsApi.get(id)); setError(false) } catch { setError(true) }
  }

  function created(ticket: Ticket) {
    setCreating(false); setTickets((current) => [ticket, ...current]); setActive(ticket)
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-zinc-950 text-zinc-100">
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-3 lg:px-6"><div className="flex items-center gap-3"><div className="rounded-lg bg-sky-500/15 p-2 text-sky-400"><TicketIcon size={18} /></div><div><h1 className="text-base font-semibold">{t("title")}</h1><p className="hidden text-xs text-zinc-500 sm:block">{t("subtitle")}</p></div></div><div className="flex items-center gap-2"><Notifications onSelect={(id) => void selectTicket(id)} /><button onClick={() => { setCreating(true); setActive(null) }} className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-3 py-2 text-xs font-medium text-white hover:bg-sky-400"><Plus size={14} />{t("newTicket")}</button></div></header>
      {error && <div className="border-b border-red-500/20 bg-red-500/5 px-4 py-2 text-xs text-red-300">{t("loadError")}</div>}
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row"><div className="flex min-h-0 flex-col lg:w-[25rem]"><TicketList tickets={tickets} filters={filters} loading={loading} activeId={active?.id ?? null} onFiltersChange={setFilters} onSelect={(id) => void selectTicket(id)} onNew={() => { setCreating(true); setActive(null) }} /><TeamSettings teams={teams} onChanged={reloadTeams} /></div>{creating ? <main className="min-h-0 flex-1 overflow-y-auto p-4 lg:p-8"><TicketForm onCreated={created} onCancel={() => setCreating(false)} /></main> : active ? <TicketDetail ticket={active} teams={teams} onUpdated={(ticket) => { setActive(ticket); void reload() }} /> : <main className="flex min-h-0 flex-1 items-center justify-center p-8 text-center"><div><TicketIcon size={36} className="mx-auto mb-3 text-zinc-700" /><p className="text-sm text-zinc-500">{t("selectTicket")}</p></div></main>}</div>
    </div>
  )
}
