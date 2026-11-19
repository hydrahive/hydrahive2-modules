import { ArrowLeft } from "lucide-react"
import { downloadReportCsv } from "./api"
import { BudgetChart, FixedCostChart } from "./BudgetFixedCharts"
import { BudgetPicker, pickBudget } from "./BudgetPicker"
import { CategoryDonut } from "./CategoryDonut"
import { CashflowChart, NetWorthChart } from "./ReportCharts"
import { ReportCard } from "./ReportCard"
import { RANGES, rangeText } from "./reportFormat"
import type { DrillStep } from "./reportLoaders"
import { BudgetTable, CashflowTable, CategoryTable, FixedCostTable, NetWorthTable } from "./ReportTables"
import type { BudgetReport, CashflowReport, CategoryReport, FixedCostReport, NetWorthReport, ReportRange } from "./types"
import { Button } from "./ui"
import type { ReportResult } from "./useReport"

type Slot<T> = { state: ReportResult<T> | undefined; retry: () => void }
export interface BoardProps {
  currency: string
  range: ReportRange
  drill: DrillStep[]
  budgetId?: number
  cashflow: Slot<CashflowReport>
  netWorth: Slot<NetWorthReport>
  categories: Slot<CategoryReport>
  budgets: Slot<BudgetReport>
  fixedCosts: Slot<FixedCostReport>
  onRange: (range: ReportRange) => void
  onDrillInto: (step: DrillStep) => void
  onDrillBack: () => void
  onBudget: (id: number) => void
}

/** Reine Darstellung der Auswertungen (alle Zustände von außen) – so ohne Browser testbar. */
export function ReportsBoard(p: BoardProps) {
  const { currency, range, drill } = p
  const within = rangeText(range)
  const last = drill[drill.length - 1]
  const budgetState = p.budgets.state
  return <div className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="max-w-xl text-sm text-[#9aa7bc]">Hier siehst du, wie sich dein Geld entwickelt. Zu jedem Diagramm gibt es eine Tabelle und einen Export als CSV-Datei (für Excel oder LibreOffice).</p>
      <div className="flex flex-wrap gap-1" role="group" aria-label="Zeitraum">{RANGES.map((item) =>
        <Button key={item.id} tone={range === item.id ? "primary" : "default"} aria-pressed={range === item.id} onClick={() => p.onRange(item.id)}>{item.label}</Button>)}</div>
    </div>
    <div className="grid gap-4 xl:grid-cols-2">
      <ReportCard title="Einnahmen und Ausgaben" hint={`Was pro Monat hereinkommt und rausgeht – ${within}. Die Linie zeigt, was übrig bleibt.`}
        {...p.cashflow} csv={() => downloadReportCsv("cashflow", range)}
        isEmpty={(d) => d.rows.every((r) => r.income === 0 && r.expense === 0)}
        chart={(d) => <CashflowChart rows={d.rows} currency={currency} />} table={(d) => <CashflowTable rows={d.rows} currency={currency} />} />
      <ReportCard title="Vermögensverlauf" hint={`Summe aller Konten am Ende jedes Monats – ${within}.`}
        {...p.netWorth} csv={() => downloadReportCsv("net-worth", range)}
        isEmpty={(d) => d.rows.length === 0}
        chart={(d) => <NetWorthChart rows={d.rows} currency={currency} />} table={(d) => <NetWorthTable rows={d.rows} currency={currency} />} />
      <ReportCard title={last ? `Ausgaben: ${last.name}` : "Ausgabenverteilung"}
        hint={last ? "Unterkategorien dieser Kategorie." : `Wofür das Geld draufgeht – ${within}. Ein Klick auf eine Kategorie mit › zeigt die Unterkategorien.`}
        {...p.categories} csv={() => downloadReportCsv("categories", range, last?.id)}
        isEmpty={(d) => d.rows.length === 0}
        extra={last && <Button onClick={p.onDrillBack}><ArrowLeft size={13} className="mr-1 inline" />Zurück</Button>}
        chart={(d) => <CategoryDonut rows={d.rows} currency={currency} onSelect={(row) => p.onDrillInto({ id: row.category_id, name: row.name })} />}
        table={(d) => <CategoryTable rows={d.rows} currency={currency} />} />
      <ReportCard title="Budget-Verlauf" hint={`Geplant (Soll) gegen tatsächlich ausgegeben (Ist), Monat für Monat – ${within}.`}
        {...p.budgets} csv={() => downloadReportCsv("budgets", range)}
        isEmpty={(d) => d.rows.length === 0} emptyText="Es gibt noch kein aktives Budget. Lege unter „Budgets“ eines an."
        extra={budgetState?.ok && <BudgetPicker rows={budgetState.data.rows} value={p.budgetId} onChange={p.onBudget} />}
        chart={(d) => <BudgetChart rows={pickBudget(d.rows, p.budgetId)} currency={currency} />}
        table={(d) => <BudgetTable rows={pickBudget(d.rows, p.budgetId)} currency={currency} />} />
      <ReportCard title="Fixkosten und variable Kosten" hint={`Feste Ausgaben (z. B. Miete, Verträge) gegenüber dem Rest – ${within}. Die Linie zeigt den Fixkosten-Anteil.`}
        {...p.fixedCosts} csv={() => downloadReportCsv("fixed-costs", range)}
        isEmpty={(d) => d.rows.every((r) => r.total === 0)}
        chart={(d) => <FixedCostChart rows={d.rows} currency={currency} />} table={(d) => <FixedCostTable rows={d.rows} currency={currency} />} />
    </div>
  </div>
}
