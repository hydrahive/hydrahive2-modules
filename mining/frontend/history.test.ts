import { describe, expect, it } from "vitest"
import { chartRows, latestTotalEur, PALETTE, perCard, seriesFor, type HistoryResponse } from "./history"

const card = (t: number, w: number) => ({ temp_c: t, power_w: w, util_pct: 90 })
const data: HistoryResponse = {
  hours: 24,
  usd_per_eur: 1.1,
  rigs: [
    { id: "a", name: "rig-a", points: [
      { ts: "2026-10-03T12:00:00+00:00", mode: "mine", coin: "cfx", usd_day: 1.1, pct: 100, cards: [card(60, 150), card(65, 160)] },
      { ts: "2026-10-03T12:01:00+00:00", mode: "mine", coin: "erg", usd_day: 2.2, pct: 98, cards: [card(61, 151), card(66, 161)] },
    ] },
    { id: "b", name: "rig-b", points: [
      { ts: "2026-10-03T12:01:00+00:00", mode: "benchmark", coin: "rvn", usd_day: null, pct: null, cards: [card(50, 120)] },
    ] },
  ],
}

describe("Serien", () => {
  it("Ertrag/Leistung: eine Linie je Rechner", () => {
    expect(seriesFor(data.rigs, "eur").map((s) => s.label)).toEqual(["rig-a", "rig-b"])
  })
  it("Watt/Temperatur: eine Linie je Karte, Kartennummer nur bei mehreren", () => {
    expect(seriesFor(data.rigs, "watt").map((s) => s.label)).toEqual(["rig-a · Karte 1", "rig-a · Karte 2", "rig-b"])
  })
  it("jede Linie eigene Farbe (bis Palettenende)", () => {
    const many = Array.from({ length: PALETTE.length }, (_, i) => ({ id: `r${i}`, name: `r${i}`, points: [] }))
    expect(new Set(seriesFor(many, "eur").map((s) => s.color)).size).toBe(PALETTE.length)
    expect(perCard("temp")).toBe(true)
    expect(perCard("eur")).toBe(false)
  })
})

describe("Zeilen", () => {
  it("Ertrag in EUR, Zeitpunkte zusammengeführt, Lücke bleibt null-frei weg", () => {
    const rows = chartRows(data, "eur")
    expect(rows).toHaveLength(2)
    expect(rows[0].a).toBeCloseTo(1.0)
    expect(rows[1].a).toBeCloseTo(2.0)
    expect(rows[1].b).toBeNull()
    expect(rows[1]["a:coin"]).toBe("erg")
    expect(rows[1]["b:coin"]).toBe("benchmark")
  })
  it("Watt je Karte", () => {
    const rows = chartRows(data, "watt")
    expect(rows[1]["a#1"]).toBe(161)
    expect(rows[1]["b#0"]).toBe(120)
  })
  it("ohne Wechselkurs kein EUR-Wert", () => {
    expect(chartRows({ ...data, usd_per_eur: null }, "eur")[0].a).toBeNull()
    expect(latestTotalEur({ ...data, usd_per_eur: null })).toBeNull()
  })
  it("Gesamtertrag = Summe der letzten Werte", () => {
    expect(latestTotalEur(data)).toBeCloseTo(2.0)
  })
})
