import { moneyFormatter, monthLabel, percentLabel } from "./reportFormat"
import { ReportTable } from "./ReportTable"
import type { BudgetReportRow, CashflowRow, CategoryReportRow, FixedCostRow, NetWorthRow } from "./types"

// Tabellenalternativen: dieselben Server-Zeilen wie im Diagramm, nur formatiert.
export function CashflowTable({ rows, currency }: { rows: CashflowRow[]; currency: string }) {
  const m = moneyFormatter(currency)
  return <ReportTable caption="Einnahmen und Ausgaben je Monat" rows={rows} columns={[
    { label: "Monat", cell: (r) => monthLabel(r.month) }, { label: "Einnahmen", right: true, cell: (r) => m(r.income) },
    { label: "Ausgaben", right: true, cell: (r) => m(r.expense) }, { label: "Netto", right: true, cell: (r) => m(r.net) }]} />
}
export function NetWorthTable({ rows, currency }: { rows: NetWorthRow[]; currency: string }) {
  const m = moneyFormatter(currency)
  return <ReportTable caption="Vermögen am Monatsende" rows={rows} columns={[
    { label: "Monat", cell: (r) => monthLabel(r.month) }, { label: "Vermögen", right: true, cell: (r) => m(r.balance) }]} />
}
export function CategoryTable({ rows, currency }: { rows: CategoryReportRow[]; currency: string }) {
  const m = moneyFormatter(currency)
  return <ReportTable caption="Ausgaben je Kategorie" rows={rows} columns={[
    { label: "Kategorie", cell: (r) => r.name }, { label: "Betrag", right: true, cell: (r) => m(r.amount) },
    { label: "Anteil", right: true, cell: (r) => percentLabel(r.share_bp) }]} />
}
export function BudgetTable({ rows, currency }: { rows: BudgetReportRow[]; currency: string }) {
  const m = moneyFormatter(currency)
  return <ReportTable caption="Budget: geplant und ausgegeben je Monat" rows={rows} columns={[
    { label: "Monat", cell: (r) => monthLabel(r.month) }, { label: "Geplant", right: true, cell: (r) => m(r.planned) },
    { label: "Ausgegeben", right: true, cell: (r) => m(r.spent) }, { label: "Übrig", right: true, cell: (r) => m(r.remaining) },
    { label: "Verbraucht", right: true, cell: (r) => percentLabel(r.used_bp) }]} />
}
export function FixedCostTable({ rows, currency }: { rows: FixedCostRow[]; currency: string }) {
  const m = moneyFormatter(currency)
  return <ReportTable caption="Feste und variable Kosten je Monat" rows={rows} columns={[
    { label: "Monat", cell: (r) => monthLabel(r.month) }, { label: "Fix", right: true, cell: (r) => m(r.fixed) },
    { label: "Variabel", right: true, cell: (r) => m(r.variable) }, { label: "Gesamt", right: true, cell: (r) => m(r.total) },
    { label: "Fix-Anteil", right: true, cell: (r) => percentLabel(r.fixed_bp) }]} />
}
