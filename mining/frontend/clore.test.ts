import { describe, expect, it } from "vitest"
import { bestRoi, cloreLine, gpuLabel, toEur } from "./clore"

describe("Clore-Probelauf: Anzeige", () => {
  it("Kartenname lesbar", () => {
    expect(gpuLabel("nvidia-rtx-3060-ti", 2)).toBe("2× RTX 3060 Ti")
    expect(gpuLabel("nvidia-v100", 8)).toBe("8× V100")
    expect(gpuLabel(null, 1)).toBe("—")
  })
  it("bester ROI aus On-Demand und Spot", () => {
    expect(bestRoi({ roi_od: 0.2, roi_spot: 0.5 })).toEqual({ roi: 0.5, kind: "spot" })
    expect(bestRoi({ roi_od: 0.3, roi_spot: null })).toEqual({ roi: 0.3, kind: "od" })
    expect(bestRoi({ roi_od: null, roi_spot: null })).toEqual({ roi: null, kind: null })
  })
  it("USD → EUR, ohne Kurs null", () => {
    expect(toEur(2.5, 1.25)).toBeCloseTo(2.0)
    expect(toEur(2.5, null)).toBeNull()
    expect(toEur(null, 1.25)).toBeNull()
  })
  it("Zeile: letzter Lauf mit/ohne Treffer, Fehler, nie gelaufen", () => {
    expect(cloreLine(null)).toEqual({ kind: "never" })
    expect(cloreLine({ ok: false, error: "timeout", free: 0, rated: 0, hits: 0, best_roi: null, ts: "x" }))
      .toEqual({ kind: "error", error: "timeout" })
    expect(cloreLine({ ok: true, free: 1400, rated: 500, hits: 0, best_roi: -0.1, ts: "x" }))
      .toEqual({ kind: "none", rated: 500, best: -0.1 })
    expect(cloreLine({ ok: true, free: 1400, rated: 500, hits: 3, best_roi: 0.4, ts: "x" }))
      .toEqual({ kind: "hits", rated: 500, hits: 3, best: 0.4 })
  })
})
