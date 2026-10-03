import { describe, expect, it } from "vitest"
import { formatHashrate, formatMoney, isStale, minutesSince } from "./format"

describe("formatHashrate", () => {
  it("wählt die passende Einheit", () => {
    expect(formatHashrate(32e6)).toBe("32.0 MH/s")
    expect(formatHashrate(91e12)).toBe("91.0 TH/s")
    expect(formatHashrate(8300)).toBe("8.30 kH/s")
    expect(formatHashrate(6.5)).toBe("6.50 H/s")
    expect(formatHashrate(125.5e6)).toBe("126 MH/s")
  })
  it("zeigt Strich bei fehlenden Werten", () => {
    expect(formatHashrate(null)).toBe("—")
    expect(formatHashrate(0)).toBe("—")
    expect(formatHashrate(Number.NaN)).toBe("—")
  })
})

describe("formatMoney", () => {
  it("formatiert Euro deutsch", () => {
    expect(formatMoney(1.5, "EUR")).toMatch(/^1,50\s€$/)
    expect(formatMoney(null, "EUR")).toBe("—")
  })
  it("zeigt zwei Nachkommastellen, kleine Beträge drei", () => {
    expect(formatMoney(1.811, "EUR")).toMatch(/^1,81\s€$/)
    expect(formatMoney(54.344, "EUR")).toMatch(/^54,34\s€$/)
    expect(formatMoney(0.0734, "EUR")).toMatch(/^0,073\s€$/)
    expect(formatMoney(0, "EUR")).toMatch(/^0,00\s€$/)
  })
})

describe("Stand der Daten", () => {
  const now = Date.parse("2026-10-03T12:00:00Z")
  it("rechnet Minuten", () => {
    expect(minutesSince("2026-10-03T11:50:00+00:00", now)).toBe(10)
    expect(minutesSince(null, now)).toBeNull()
    expect(minutesSince("kaputt", now)).toBeNull()
  })
  it("gilt ab 16 min als veraltet", () => {
    expect(isStale("2026-10-03T11:45:00+00:00", now)).toBe(false)
    expect(isStale("2026-10-03T11:44:00+00:00", now)).toBe(true)
    expect(isStale(null, now)).toBe(true)
  })
})
