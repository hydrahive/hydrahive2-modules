// A1 – Kostengrenze je Auftrag (Spec kostengrenze.md): reine Hilfen ohne React.
import { describe, expect, it } from "vitest"
import { LIMIT_MAX, LIMIT_MIN, limitCents, overLimit, parseLimit, totalTokens } from "./costLimit"

describe("costLimit", () => {
  it("gesamt = Eingabe + Ausgabe", () => {
    expect(totalTokens({ input_tokens: 900, output_tokens: 500 })).toBe(1400)
  })
  it("über der Grenze zählt Eingabe mit; gleich ist nicht darüber; 0 = aus", () => {
    const est = { input_tokens: 900, output_tokens: 500 }
    expect(overLimit(est, 1000)).toBe(true)        // Ausgabe allein (500) läge darunter
    expect(overLimit(est, 1400)).toBe(false)
    expect(overLimit(est, 1399)).toBe(true)
    expect(overLimit(est, 0)).toBe(false)
    expect(overLimit(null, 1000)).toBe(false)
  })
  it("Eingabe prüfen: leer/0 = aus, sonst im Bereich, ganze Zahl", () => {
    expect(parseLimit("")).toEqual({ ok: true, value: 0 })
    expect(parseLimit("0")).toEqual({ ok: true, value: 0 })
    expect(parseLimit("1000")).toEqual({ ok: true, value: LIMIT_MIN })
    expect(parseLimit("20000000")).toEqual({ ok: true, value: LIMIT_MAX })
    expect(parseLimit(" 50 000 ")).toEqual({ ok: true, value: 50_000 })   // Leerzeichen/Tausenderpunkte erlaubt
    expect(parseLimit("50.000")).toEqual({ ok: true, value: 50_000 })
    for (const bad of ["999", "20000001", "-5", "abc", "1,5"]) expect(parseLimit(bad).ok).toBe(false)
  })
  it("Grenze in Cent, hochgerechnet mit dem Preis der Schätzung; unbekannt → null", () => {
    const est = { input_tokens: 800, output_tokens: 200, cost_micros: 5000 }   // 1000 Tokens = 5 Cent
    expect(limitCents(est, 4000)).toBe("20.00")
    expect(limitCents({ ...est, cost_micros: null }, 4000)).toBeNull()
    expect(limitCents(est, 0)).toBeNull()
    expect(limitCents({ input_tokens: 0, output_tokens: 0, cost_micros: 0 }, 4000)).toBeNull()
  })
})
