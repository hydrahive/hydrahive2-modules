// Abruf-Bausteine für die Auswertungen: reine Funktionen, damit Zeitraumwechsel und Drilldown ohne Browser testbar sind.
import { haushaltsbuchApi } from "./api"
import type { ReportRange } from "./types"

export type ReportsApi = Pick<typeof haushaltsbuchApi,
  "reportCashflow" | "reportNetWorth" | "reportCategories" | "reportBudgets" | "reportFixedCosts">

export interface DrillStep { id: number; name: string }

/** Eine Fabrik je Zeitraum: Änderung des Zeitraums ⇒ neue Funktionen ⇒ neuer Abruf. */
export function reportLoaders(api: ReportsApi, range: ReportRange, drill: DrillStep[]) {
  const parentId = drill.length ? drill[drill.length - 1].id : undefined
  return {
    cashflow: () => api.reportCashflow(range),
    netWorth: () => api.reportNetWorth(range),
    categories: () => api.reportCategories(range, parentId),
    budgets: () => api.reportBudgets(range),
    fixedCosts: () => api.reportFixedCosts(range),
  }
}

export const drillInto = (drill: DrillStep[], step: DrillStep): DrillStep[] => [...drill, step]
export const drillBack = (drill: DrillStep[]): DrillStep[] => drill.slice(0, -1)
