import { useMemo, useState } from "react"
import { haushaltsbuchApi } from "./api"
import { drillBack, drillInto, reportLoaders, type DrillStep } from "./reportLoaders"
import { ReportsBoard } from "./ReportsBoard"
import type { Household, ReportRange } from "./types"
import { useReport } from "./useReport"

/** Tab „Auswertungen“: hält Zeitraum, Drilldown und Budget-Auswahl und lädt die fünf Reports. */
export function ReportsView({ household }: { household: Household }) {
  const [range, setRange] = useState<ReportRange>("12")
  const [drill, setDrill] = useState<DrillStep[]>([])
  const [budgetId, setBudgetId] = useState<number>()
  const loaders = useMemo(() => reportLoaders(haushaltsbuchApi, range, drill), [range, drill])
  const cashflow = useReport(loaders.cashflow)
  const netWorth = useReport(loaders.netWorth)
  const categories = useReport(loaders.categories)
  const budgets = useReport(loaders.budgets)
  const fixedCosts = useReport(loaders.fixedCosts)
  return <ReportsBoard currency={household.base_currency} range={range} drill={drill} budgetId={budgetId}
    cashflow={cashflow} netWorth={netWorth} categories={categories} budgets={budgets} fixedCosts={fixedCosts}
    onRange={(next) => { setRange(next); setDrill([]) }} onDrillInto={(step) => setDrill(drillInto(drill, step))}
    onDrillBack={() => setDrill(drillBack(drill))} onBudget={setBudgetId} />
}
