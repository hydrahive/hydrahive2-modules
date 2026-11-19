// Achsenbeschriftung: Minor-Units müssen in der Kurzform auf die richtige Größenordnung kommen.
import { describe, expect, it, vi } from "vitest"

vi.stubGlobal("navigator", { language: "de-DE" })
import { compactMoney, percentLabel } from "./reportFormat"

const compact = (value: number, currency: string) =>
  new Intl.NumberFormat("de-DE", { style: "currency", currency, notation: "compact" }).format(value)

describe("reportFormat", () => {
  it("rechnet Cent in der Kurzform korrekt in Euro um", () => {
    expect(compactMoney(123456, "EUR")).toBe(compact(1234.56, "EUR"))
    expect(compactMoney(250_000_000, "EUR")).toBe(compact(2_500_000, "EUR"))
    expect(compactMoney(250_000_000, "EUR")).toMatch(/^2,5\s?Mio\.\s?€$/)
  })
  it("berücksichtigt Währungen ohne Nachkommastellen", () => {
    expect(compactMoney(2_500_000, "JPY")).toBe(compact(2_500_000, "JPY"))
  })
  it("zeigt Basispunkte als Prozent", () => {
    expect(percentLabel(2550)).toBe("25,5 %")
  })
})
