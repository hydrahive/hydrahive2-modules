import { useEffect, useState } from "react"
import { ArrowDownRight, ArrowUpRight, CalendarClock, Gauge, Landmark, TriangleAlert } from "lucide-react"
import { errorMessage, haushaltsbuchApi, isConflict } from "./api"
import { formatMinorUnits } from "./money"
import type { Dashboard, Household } from "./types"
import { EmptyState, ErrorState, LoadingState, Progress, panel } from "./ui"

export function DashboardView({ household, refreshKey = 0 }: { household: Household; refreshKey?: number }) {
  const [data, setData] = useState<Dashboard>()
  const [error, setError] = useState<unknown>()
  const load = () => { setError(undefined); haushaltsbuchApi.dashboard().then(setData).catch(setError) }
  useEffect(load, [refreshKey])
  if (error) return <ErrorState error={errorMessage(error)} conflict={isConflict(error)} onRetry={load} />
  if (!data) return <LoadingState label="Übersicht wird berechnet …" />
  const money = (value: number) => formatMinorUnits(value, household.base_currency)
  const budgetPercent = data.budget_amount ? data.budget_spent * 100 / data.budget_amount : 0
  return <div className="space-y-4">
    {data.forecast_30.warnings.length > 0 && <div className="flex gap-3 rounded-[6px] border border-amber-500/35 bg-amber-500/10 p-4 text-sm text-amber-100"><TriangleAlert className="shrink-0" size={18} /><div><strong>Prognostizierte Unterdeckung</strong><p className="mt-1 opacity-80">Am {new Date(`${data.forecast_30.warnings[0].date}T12:00:00`).toLocaleDateString()} liegt der erwartete Saldo bei {money(data.forecast_30.warnings[0].projected_balance)}.</p></div></div>}
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric icon={<Landmark size={17} />} label="Gesamtsaldo" value={money(data.total_balance)} />
      <Metric icon={<ArrowUpRight size={17} />} label="Einnahmen diesen Monat" value={money(data.month_income)} />
      <Metric icon={<ArrowDownRight size={17} />} label="Ausgaben diesen Monat" value={money(data.month_expense)} />
      <Metric icon={<Gauge size={17} />} label="90-Tage-Prognose" value={money(data.forecast_90.closing_balance)} hint={`${money(data.forecast_90.net_change)} Veränderung`} />
    </div>
    <div className="grid gap-4 xl:grid-cols-2">
      <section className={`${panel} p-4`}><h2 className="mb-4 font-bold text-[#e8eef8]">Budgetverbrauch</h2>{data.budget_amount ? <><Progress value={budgetPercent} label={`${money(data.budget_spent)} von ${money(data.budget_amount)}`} /><p className="mt-3 text-xs text-[#718097]">Fortschritt wird zusätzlich als Prozentwert angezeigt und nicht nur farblich vermittelt.</p></> : <p className="text-sm text-[#8d9ab0]">Noch keine aktiven Budgets.</p>}</section>
      <section className={`${panel} p-4`}><h2 className="mb-3 flex items-center gap-2 font-bold text-[#e8eef8]"><CalendarClock size={17} className="text-cyan-300" />Nächste Zahlungen</h2>{data.upcoming.length ? <div className="divide-y divide-[#263247]">{data.upcoming.slice(0, 5).map((item, i) => <div key={`${item.rule_id}-${item.due_date}-${i}`} className="flex items-center gap-3 py-2 text-sm"><span className="w-24 text-[#8d9ab0]">{new Date(`${item.due_date}T12:00:00`).toLocaleDateString()}</span><span className="min-w-0 flex-1 truncate text-[#d4deeb]">{item.counterparty || "Ohne Vertragspartner"}</span><strong className={item.effect < 0 ? "text-rose-200" : "text-emerald-200"}>{money(item.effect)}</strong></div>)}</div> : <p className="text-sm text-[#8d9ab0]">Keine bestätigten Fälligkeiten.</p>}</section>
    </div>
    <section><h2 className="mb-3 font-bold text-[#e8eef8]">Letzte Buchungen</h2>{data.recent_transactions.length ? <div className={`${panel} divide-y divide-[#263247]`}>{data.recent_transactions.map((tx) => <div key={tx.id} className="grid grid-cols-[7rem_1fr_auto] gap-3 px-4 py-3 text-sm"><span className="text-[#8d9ab0]">{new Date(`${tx.booking_date}T12:00:00`).toLocaleDateString()}</span><span className="truncate text-[#d4deeb]">{tx.counterparty || tx.purpose || `Buchung #${tx.id}`}</span><span className="text-xs uppercase text-[#718097]">{tx.status === "reversed" ? "Storniert" : "Gebucht"}</span></div>)}</div> : <EmptyState title="Noch keine Buchungen" text="Erfasse die erste Einnahme, Ausgabe oder Umbuchung." />}</section>
  </div>
}
function Metric({ icon, label, value, hint }: { icon: React.ReactNode; label: string; value: string; hint?: string }) { return <div className={`${panel} p-4`}><div className="flex items-center gap-2 text-xs font-semibold text-[#8d9ab0]">{icon}{label}</div><div className="mt-2 text-xl font-black tabular-nums text-[#e8eef8]">{value}</div>{hint && <p className="mt-1 text-xs text-[#718097]">{hint}</p>}</div> }
