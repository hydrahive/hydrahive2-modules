import { useCallback, useEffect, useState } from "react"
import { Bell, Plus, Ticket as TicketIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
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
    try {
      setTickets(await ticketsApi.list(filters))
      setError(false)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [filters])

  const reloadTeams = useCallback(() => {
    void ticketsApi.teams().then(setTeams).catch(() => setTeams([]))
  }, [])

  useEffect(() => { void reload() }, [reload])
  useEffect(() => { reloadTeams() }, [reloadTeams])

  async function selectTicket(id: string) {
    setCreating(false)
    try {
      setActive(await ticketsApi.get(id))
      setError(false)
    } catch {
      setError(true)
    }
  }

  function startCreating() {
    setCreating(true)
    setActive(null)
  }

  function created(ticket: Ticket) {
    setCreating(false)
    setTickets((current) => [ticket, ...current])
    setActive(ticket)
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-[#080b11] text-[#e8eef8]">
      <CockpitTopbar active="/tickets" context={t("subtitle")} />
      <header className="flex min-h-[68px] shrink-0 items-center justify-between border-b border-[#1f2a3b] bg-[#0d1420] px-4 lg:px-6">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-[8px] border border-[#2b4058] bg-[#132235] text-[#69d7ff]"><TicketIcon size={18} /></div>
          <div>
            <div className="flex items-center gap-2"><h1 className="text-[15px] font-semibold tracking-[-0.01em] text-[#f1f5fb]">{t("title")}</h1><span className="rounded-[4px] border border-[#29405a] bg-[#122234] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.1em] text-[#76dfff]">{t("internalBadge")}</span></div>
            <p className="mt-0.5 hidden text-[11px] text-[#718096] sm:block">{t("subtitle")}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Notifications onSelect={(id) => void selectTicket(id)} />
          <button onClick={startCreating} className="inline-flex items-center gap-2 rounded-[7px] border border-[#3b83a8] bg-[#163248] px-3 py-2 text-xs font-semibold text-[#c8f2ff] transition-colors hover:border-[#69d7ff] hover:bg-[#1b3d56]"><Plus size={14} />{t("newTicket")}</button>
        </div>
      </header>

      {error && <div className="flex items-center gap-2 border-b border-orange-500/25 bg-orange-500/[7%] px-5 py-2 text-xs text-orange-200"><Bell size={13} />{t("loadError")}</div>}

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <div className="flex min-h-0 flex-col lg:w-[292px]">
          <TicketList tickets={tickets} filters={filters} loading={loading} activeId={active?.id ?? null} onFiltersChange={setFilters} onSelect={(id) => void selectTicket(id)} onNew={startCreating} />
          <TeamSettings teams={teams} onChanged={reloadTeams} />
        </div>
        {creating ? <main className="min-h-0 flex-1 overflow-y-auto bg-[#0a1019] p-4 lg:p-8"><TicketForm onCreated={created} onCancel={() => setCreating(false)} /></main> : active ? <TicketDetail ticket={active} teams={teams} onUpdated={(ticket) => { setActive(ticket); void reload() }} /> : <main className="flex min-h-0 flex-1 items-center justify-center bg-[#0a1019] p-8 text-center"><div className="max-w-sm"><div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-[10px] border border-[#253247] bg-[#111b29] text-[#607188]"><TicketIcon size={21} /></div><h2 className="text-sm font-semibold text-[#c8d2df]">{t("selectTicketTitle")}</h2><p className="mt-2 text-xs leading-relaxed text-[#68788e]">{t("selectTicket")}</p><button onClick={startCreating} className="mt-5 inline-flex items-center gap-2 rounded-[7px] border border-[#2b4058] bg-[#111b29] px-3 py-2 text-xs font-semibold text-[#a8dff2] hover:border-[#69d7ff]/60 hover:bg-[#163248]"><Plus size={14} />{t("newTicket")}</button></div></main>}
      </div>
    </div>
  )
}
