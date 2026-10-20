import { describe, expect, it } from "vitest"
import { DIN, DELIVERY_LABEL, checkSummary, deDate, entryLabel, splitBody } from "./letterFormat"

describe("deDate", () => {
  it("ISO → „20. Oktober 2026“ (DIN 5008, ausgeschrieben)", () => {
    expect(deDate("2026-10-20")).toBe("20. Oktober 2026")
    expect(deDate("2026-03-01")).toBe("1. März 2026")
    expect(deDate("")).toBe("")
    expect(deDate("kaputt")).toBe("kaputt")
  })
})

describe("DIN-Maße Form B (falzmarke.com, mehrfach belegt)", () => {
  it("stimmen mit der Quelle überein", () => {
    expect(DIN).toEqual({
      headerMm: 45, addressLeftMm: 20, addressTextLeftMm: 25, addressWidthMm: 85, addressHeightMm: 45,
      returnMm: 5, notesMm: 12.7, recipientMm: 27.3, infoLeftMm: 125, infoWidthMm: 75, infoTopMm: 50,
      marginLeftMm: 25, marginRightMm: 20, foldMm: [105, 210], punchMm: 148.5, lineMm: 4.23,
    })
    expect(DIN.addressLeftMm + DIN.addressWidthMm).toBeLessThanOrEqual(DIN.infoLeftMm)
    expect(210 - DIN.marginLeftMm - DIN.marginRightMm).toBe(165)
    expect(DIN.returnMm + DIN.notesMm + DIN.recipientMm).toBeCloseTo(DIN.addressHeightMm, 5)
  })
})

describe("checkSummary", () => {
  it("zählt offene Punkte und rote Normen", () => {
    const s = checkSummary({ ok: false, items: [{ key: "a", ok: true, hint: "" }, { key: "b", ok: false, hint: "x" }],
      norms: [{ raw: "§ 1", citation: "§ 1 BGB", found: true }, { raw: "§ 999", citation: "§ 999 BGB", found: false }] })
    expect(s).toEqual({ open: 1, total: 2, badNorms: ["§ 999 BGB"], ok: false })
    expect(checkSummary(null)).toEqual({ open: 0, total: 0, badNorms: [], ok: false })
  })
})

describe("splitBody", () => {
  it("trennt Anrede, Absätze, Gruß – und markiert [Platzhalter]", () => {
    const parts = splitBody("Sehr geehrte Damen und Herren,\n\nText [Datum] hier.\n\nMit freundlichen Grüßen")
    expect(parts.map((p) => p.text)).toEqual(["Sehr geehrte Damen und Herren,", "Text [Datum] hier.", "Mit freundlichen Grüßen"])
    expect(parts[1].placeholders).toEqual(["[Datum]"])
  })
})

describe("entryLabel", () => {
  it("beschreibt Richtung, Status und Zustellweg", () => {
    expect(entryLabel({ direction: "out", status: "draft", delivery: "", date: "" })).toBe("Ausgang · Entwurf")
    expect(entryLabel({ direction: "out", status: "sent", delivery: "einwurf_einschreiben", date: "2026-10-21" }))
      .toBe("Ausgang · versendet 21. Oktober 2026 · Einwurf-Einschreiben")
    expect(entryLabel({ direction: "in", status: "received", delivery: "", date: "2026-10-15" }))
      .toBe("Eingang · 15. Oktober 2026")
    expect(DELIVERY_LABEL.bote).toBe("Bote")
  })
})
