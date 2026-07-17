import { useCallback, useEffect, useState, type ComponentType } from "react"
import { CalendarClock, Gauge, Home, Landmark, ReceiptText, Users } from "lucide-react"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { AccountsView } from "./AccountsView"
import { errorMessage, haushaltsbuchApi, isNotFound } from "./api"
import { BudgetsView } from "./BudgetsView"
import { DashboardView } from "./DashboardView"
import { HouseholdSetup } from "./HouseholdSetup"
import { HouseholdView } from "./HouseholdView"
import { RecurringView } from "./RecurringView"
import { TransactionsView } from "./TransactionsView"
import type { Household } from "./types"
import { Button, ErrorState, LoadingState } from "./ui"

type View = "dashboard" | "transactions" | "accounts" | "budgets" | "recurring" | "household"
const TABS: { id: View; label: string; icon: ComponentType<{ size?: number }> }[] = [
  { id: "dashboard", label: "Übersicht", icon: Home },
  { id: "transactions", label: "Buchungen", icon: ReceiptText },
  { id: "accounts", label: "Konten & Kategorien", icon: Landmark },
  { id: "budgets", label: "Budgets", icon: Gauge },
  { id: "recurring", label: "Wiederkehrend", icon: CalendarClock },
  { id: "household", label: "Haushalt", icon: Users },
]

export function HaushaltsbuchPage() {
  const [household, setHousehold] = useState<Household | null>()
  const [error, setError] = useState<unknown>()
  const [view, setView] = useState<View>("dashboard")
  const [refreshKey, setRefreshKey] = useState(0)

  const loadHousehold = useCallback(() => {
    setError(undefined)
    haushaltsbuchApi.household().then(setHousehold).catch((cause) => {
      if (isNotFound(cause)) setHousehold(null)
      else setError(cause)
    })
  }, [])
  useEffect(loadHousehold, [loadHousehold])

  const changed = () => setRefreshKey((value) => value + 1)
  const householdChanged = (next: Household | null) => {
    setHousehold(next)
    setRefreshKey((value) => value + 1)
    if (!next) setView("dashboard")
  }

  let content
  if (error) content = <ErrorState error={errorMessage(error)} onRetry={loadHousehold} />
  else if (household === undefined) content = <LoadingState label="Haushalt wird geladen …" />
  else if (household === null) content = <HouseholdSetup onReady={householdChanged} />
  else content = <>
    <header className="mb-4 flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-xl font-black tracking-tight text-[#e8eef8]">{household.name}</h1><p className="mt-1 text-sm text-[#8d9ab0]">{household.base_currency} · {household.timezone} · {household.current_role === "owner" ? "Eigentümer" : "Mitglied"}</p></div><Button onClick={loadHousehold}>Aktualisieren</Button></header>
    <nav className="mb-5 flex gap-1 overflow-x-auto border-b border-[#263247] pb-px" aria-label="Haushaltsbuch-Bereiche">{TABS.map((tab) => { const Icon = tab.icon; return <button key={tab.id} type="button" onClick={() => setView(tab.id)} className={`flex shrink-0 items-center gap-2 border-b-2 px-3 py-2 text-xs font-bold transition ${view === tab.id ? "border-cyan-300 text-cyan-200" : "border-transparent text-[#8d9ab0] hover:text-[#d4deeb]"}`}><Icon size={14} />{tab.label}</button> })}</nav>
    {view === "dashboard" && <DashboardView household={household} refreshKey={refreshKey} />}
    {view === "transactions" && <TransactionsView household={household} onChanged={changed} />}
    {view === "accounts" && <AccountsView household={household} onChanged={changed} />}
    {view === "budgets" && <BudgetsView household={household} onChanged={changed} />}
    {view === "recurring" && <RecurringView household={household} onChanged={changed} />}
    {view === "household" && <HouseholdView household={household} onChanged={householdChanged} />}
  </>

  return <CockpitShell title="Haushaltsbuch" className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
    <CockpitTopbar active="/haushaltsbuch" context="Finanzen, Budgets und Haushalt" />
    <main className="min-h-0 flex-1 overflow-y-auto p-[10px]"><div className="mx-auto max-w-7xl">{content}</div></main>
  </CockpitShell>
}
