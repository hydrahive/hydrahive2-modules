// Dashboard: Mini-Auswertungen unter den Kacheln; ein Fehler dort darf das Dashboard nicht kaputt machen.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.stubGlobal("navigator", { language: "de-DE" })   // Node 20 kennt navigator nicht; Formate deterministisch
vi.mock("@/shared/api-client", () => ({ api: {}, buildErrorMessage: () => "Fehler" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) } }))
import { DashboardReportPanels } from "./DashboardReports"
import { DashboardContent } from "./DashboardView"
import { cashflow, netWorth } from "./reportsFixtures"
import type { Dashboard, Household } from "./types"

const household = { id: 1, name: "Zuhause", base_currency: "EUR", timezone: "Europe/Berlin" } as Household
const dashboard = {
  total_balance: 123456, month_income: 200000, month_expense: 70000, budget_amount: 0, budget_spent: 0,
  forecast_30: { warnings: [] }, forecast_90: { closing_balance: 100000, net_change: 5000 }, upcoming: [], recent_transactions: [],
} as unknown as Dashboard
const retry = () => undefined
const ok = <T,>(data: T) => ({ state: { ok: true as const, data }, retry })
const bad = { state: { ok: false as const, error: new Error("kaputt") }, retry }

describe("Dashboard mit Mini-Auswertungen", () => {
  const render = (cf: Parameters<typeof DashboardReportPanels>[0]["cashflow"], nw: Parameters<typeof DashboardReportPanels>[0]["netWorth"]) =>
    renderToStaticMarkup(<DashboardContent data={dashboard} household={household}
      reports={<DashboardReportPanels currency="EUR" cashflow={cf} netWorth={nw} onOpenReports={() => undefined} />} />)

  it("zeigt Kennzahlen, Kurztext mit formatierten Beträgen und den Knopf „Alle Auswertungen“", () => {
    const html = render(ok(cashflow), ok(netWorth))
    expect(html).toContain("Gesamtsaldo")
    expect(html).toContain("Alle Auswertungen")
    expect(html).toContain("In den letzten 6 Monaten kamen")
    expect(html).toContain("3.299,50")
    expect(html).not.toContain("329950")
  })
  it("Report-Fehler ⇒ Dashboard bleibt sichtbar, Fehlerhinweis nur an der Stelle", () => {
    const html = render(bad, bad)
    expect(html).toContain("Gesamtsaldo")
    expect(html).toContain("Letzte Buchungen")
    expect(html).toContain("Die Auswertung konnte gerade nicht geladen werden.")
    expect(html).toContain("Alle Auswertungen")
  })
  it("Ladezustand der Mini-Charts blockiert das Dashboard nicht", () => {
    const html = render({ state: undefined, retry }, { state: undefined, retry })
    expect(html).toContain("Gesamtsaldo")
    expect(html).toContain("Wird berechnet")
  })
})
