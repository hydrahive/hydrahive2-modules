import { describe, expect, it, vi } from "vitest"
import { saveSwitch } from "./callsLogic"

describe("Schalter speichert sofort", () => {
  it("an: speichert mit der gespeicherten Ansage", async () => {
    const api = { saveCalls: vi.fn(async () => ({})) }
    const r = await saveSwitch(api, true, "Gespeicherte Ansage", false)
    expect(api.saveCalls).toHaveBeenCalledWith({ answer_calls: true, greeting: "Gespeicherte Ansage" })
    expect(r).toEqual({ value: true, error: undefined })
  })
  it("Fehler: alter Zustand bleibt, Fehlercode zurück", async () => {
    const api = { saveCalls: vi.fn(async () => { throw Object.assign(new Error("x"), { code: "rate_limited" }) }) }
    expect(await saveSwitch(api, true, "", false)).toEqual({ value: false, error: "rate_limited" })
  })
  it("Fehler ohne Code: unknown", async () => {
    const api = { saveCalls: vi.fn(async () => { throw new Error("weg") }) }
    expect(await saveSwitch(api, false, "", true)).toEqual({ value: true, error: "unknown" })
  })
})
