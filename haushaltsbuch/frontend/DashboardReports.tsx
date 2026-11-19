import { useCallback } from "react"
import { haushaltsbuchApi } from "./api"
import { CashflowChart, NetWorthChart } from "./ReportCharts"
import { moneyFormatter } from "./reportFormat"
import { Button, ErrorState, LoadingState, panel } from "./ui"
import { useReport, type ReportResult } from "./useReport"
import type { CashflowReport, Household, NetWorthReport } from "./types"

interface PanelsProps {
  currency: string
  cashflow: { state: ReportResult<CashflowReport> | undefined; retry: () => void }
  netWorth: { state: ReportResult<NetWorthReport> | undefined; retry: () => void }
  onOpenReports?: () => void
}

/** Lädt die beiden Mini-Reports. Fehler bleiben lokal: das übrige Dashboard läuft weiter. */
export function DashboardReports({ household, refreshKey = 0, onOpenReports }: { household: Household; refreshKey?: number; onOpenReports?: () => void }) {
  // refreshKey ist Teil der Abhängigkeiten: nach Änderungen wird neu geladen.
  const cashflow = useReport(useCallback(() => haushaltsbuchApi.reportCashflow("6").finally(() => void refreshKey), [refreshKey]))
  const netWorth = useReport(useCallback(() => haushaltsbuchApi.reportNetWorth("12").finally(() => void refreshKey), [refreshKey]))
  return <DashboardReportPanels currency={household.base_currency} cashflow={cashflow} netWorth={netWorth} onOpenReports={onOpenReports} />
}

export function DashboardReportPanels({ currency, cashflow, netWorth, onOpenReports }: PanelsProps) {
  const money = moneyFormatter(currency)
  const cf = cashflow.state
  const nw = netWorth.state
  return <section className="space-y-3" aria-label="Auswertungen im Überblick">
    <div className="flex items-center justify-between gap-3"><h2 className="font-bold text-[#e8eef8]">Entwicklung</h2>{onOpenReports && <Button onClick={onOpenReports}>Alle Auswertungen</Button>}</div>
    <div className="grid gap-4 xl:grid-cols-2">
      <div className={`${panel} p-4`}>
        <h3 className="text-sm font-bold text-[#e8eef8]">Einnahmen und Ausgaben (6 Monate)</h3>
        {!cf ? <LoadingState label="Wird berechnet …" /> : !cf.ok ? <div className="mt-2"><ErrorState error="Die Auswertung konnte gerade nicht geladen werden." onRetry={cashflow.retry} /></div> : <>
          <p className="mb-2 mt-1 text-xs text-[#9aa7bc]">In den letzten 6 Monaten kamen {money(cf.data.totals.income)} herein und {money(cf.data.totals.expense)} gingen raus – unterm Strich {money(cf.data.totals.net)}.</p>
          <CashflowChart rows={cf.data.rows} currency={currency} mini />
        </>}
      </div>
      <div className={`${panel} p-4`}>
        <h3 className="text-sm font-bold text-[#e8eef8]">Vermögensverlauf (12 Monate)</h3>
        {!nw ? <LoadingState label="Wird berechnet …" /> : !nw.ok ? <div className="mt-2"><ErrorState error="Die Auswertung konnte gerade nicht geladen werden." onRetry={netWorth.retry} /></div> : <>
          <p className="mb-2 mt-1 text-xs text-[#9aa7bc]">Dein Vermögen liegt jetzt bei {money(nw.data.totals.end_balance)} – {money(nw.data.totals.change)} Veränderung gegenüber dem Start des Zeitraums.</p>
          <NetWorthChart rows={nw.data.rows} currency={currency} mini />
        </>}
      </div>
    </div>
  </section>
}
