// Auswertungen: Tabellenalternative mit formatierten Beträgen, Zeitraumwechsel ⇒ neuer Abruf, Drilldown ⇒ Abruf mit parentId.
// Ohne Browser-Umgebung (der Kern hat kein jsdom): statisches Markup + die reinen Abruf-Bausteine mit gemockter api.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.stubGlobal("navigator", { language: "de-DE" })   // Node 20 kennt navigator nicht; Formate deterministisch
vi.mock("@/shared/api-client", () => ({ api: {}, buildErrorMessage: () => "Fehler" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) } }))
import { budgets, cashflow, categories, fixedCosts, netWorth } from "./reportsFixtures"
import { drillBack, drillInto, reportLoaders, type ReportsApi } from "./reportLoaders"
import { ReportsBoard, type BoardProps } from "./ReportsBoard"
import { formatMinorUnits } from "./money"

const ok = <T,>(data: T) => ({ state: { ok: true as const, data }, retry: () => undefined })
const board = (over: Partial<BoardProps> = {}) => renderToStaticMarkup(<ReportsBoard currency="EUR" range="12" drill={[]}
  cashflow={ok(cashflow)} netWorth={ok(netWorth)} categories={ok(categories)} budgets={ok(budgets)} fixedCosts={ok(fixedCosts)}
  onRange={() => undefined} onDrillInto={() => undefined} onDrillBack={() => undefined} onBudget={() => undefined} {...over} />)
const fakeApi = (): ReportsApi => ({
  reportCashflow: vi.fn().mockResolvedValue(cashflow), reportNetWorth: vi.fn().mockResolvedValue(netWorth),
  reportCategories: vi.fn().mockResolvedValue(categories), reportBudgets: vi.fn().mockResolvedValue(budgets),
  reportFixedCosts: vi.fn().mockResolvedValue(fixedCosts),
})

describe("ReportsBoard", () => {
  it("zeigt die Tabellenalternative je Diagramm mit formatierten Beträgen", () => {
    const html = board()
    expect(html.match(/Als Tabelle anzeigen/g)).toHaveLength(5)
    for (const cents of [200000, 70000, 329950, 60000, 42000, 80000]) expect(html).toContain(formatMinorUnits(cents, "EUR"))
    expect(html).not.toContain("329950")
    expect(html).toContain("60,0 %")
    expect(html).toContain("66,6 %")
    expect(html).toContain("in den letzten 12 Monaten")
  })
  it("hat Zeitraumwahl, CSV je Diagramm und die deutschen Texte", () => {
    const html = board({ range: "all" })
    for (const label of ["3 Monate", "6 Monate", "12 Monate", "24 Monate", "Seit Beginn"]) expect(html).toContain(label)
    expect(html).toMatch(/aria-pressed="true"[^>]*>Seit Beginn/)
    expect(html.match(/als CSV-Datei herunterladen/g)).toHaveLength(5)
    expect(html).toContain("Fixkosten und variable Kosten")
  })
  it("Drilldown zeigt Titel der Kategorie und „Zurück“", () => {
    const html = board({ drill: [{ id: 7, name: "Wohnen" }] })
    expect(html).toContain("Ausgaben: Wohnen")
    expect(html).toContain("Zurück")
    expect(board()).not.toContain("Zurück")
  })
  it("Laden, Fehler und leere Daten werden je Diagramm getrennt gezeigt", () => {
    const html = board({
      cashflow: { state: undefined, retry: () => undefined },
      netWorth: { state: { ok: false, error: new Error("Server weg") }, retry: () => undefined },
      categories: ok({ ...categories, rows: [] }),
    })
    expect(html).toContain("Auswertung wird berechnet")
    expect(html).toContain("Server weg")
    expect(html).toContain("Noch nichts auszuwerten")
    expect(html).toContain("Fixkosten und variable Kosten")
  })
  it("leeres Budget-Verlauf-Diagramm erklärt, was zu tun ist", () => {
    expect(board({ budgets: ok({ ...budgets, rows: [] }) })).toContain("Es gibt noch kein aktives Budget")
  })
})

describe("Abrufe", () => {
  it("Zeitraumwechsel ⇒ alle fünf Reports werden mit dem neuen Zeitraum abgerufen", async () => {
    const api = fakeApi()
    const first = reportLoaders(api, "12", [])
    const second = reportLoaders(api, "3", [])
    expect(second.cashflow).not.toBe(first.cashflow)   // neue Funktion ⇒ useReport lädt neu
    await Promise.all(Object.values(second).map((load) => load()))
    expect(api.reportCashflow).toHaveBeenCalledWith("3")
    expect(api.reportNetWorth).toHaveBeenCalledWith("3")
    expect(api.reportBudgets).toHaveBeenCalledWith("3")
    expect(api.reportFixedCosts).toHaveBeenCalledWith("3")
    expect(api.reportCategories).toHaveBeenCalledWith("3", undefined)
  })
  it("Drilldown ⇒ Abruf mit parentId, Zurück ⇒ wieder ohne", async () => {
    const api = fakeApi()
    const drill = drillInto([], { id: 7, name: "Wohnen" })
    await reportLoaders(api, "6", drill).categories()
    expect(api.reportCategories).toHaveBeenLastCalledWith("6", 7)
    await reportLoaders(api, "6", drillBack(drill)).categories()
    expect(api.reportCategories).toHaveBeenLastCalledWith("6", undefined)
  })
})
