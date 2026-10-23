import { describe, expect, it } from "vitest"
import { errorCode, looksMicrosoft, nextState, pollDelayMs, safeLink, startErrorKey } from "./msFlow"

describe("Microsoft-Anmeldung – Logik", () => {
  it("Antwort des Servers → Zustand", () => {
    expect(nextState({ state: "pending" })).toBe("waiting")
    expect(nextState({ state: "done" })).toBe("done")
    expect(nextState({ state: "expired" })).toBe("expired")
    expect(nextState({ state: "denied" })).toBe("denied")
    expect(nextState({ state: "error" })).toBe("error")
    expect(nextState({ state: "irgendwas" })).toBe("error")
  })

  it("Takt: nie schneller als Microsoft erlaubt, aber 2–30 s", () => {
    expect(pollDelayMs(5)).toBe(5000)
    expect(pollDelayMs(0)).toBe(2000)
    expect(pollDelayMs(999)).toBe(30000)
    expect(pollDelayMs(Number.NaN)).toBe(5000)
  })

  it("Link nur zu Microsoft", () => {
    expect(safeLink("https://microsoft.com/devicelogin")).toBe("https://microsoft.com/devicelogin")
    expect(safeLink("https://login.microsoft.com/device")).toBe("https://login.microsoft.com/device")
    expect(safeLink("https://microsoft.com.boese.example/x")).toBe("https://microsoft.com/devicelogin")
    expect(safeLink("javascript:alert(1)")).toBe("https://microsoft.com/devicelogin")
  })

  it("Fehlercodes beim Start → Textschlüssel", () => {
    expect(startErrorKey("microsoft_not_configured")).toBe("ms.err.notConfigured")
    expect(startErrorKey("too_many_flows")).toBe("ms.err.tooMany")
    expect(startErrorKey("microsoft")).toBe("ms.err.microsoft")
    expect(startErrorKey(undefined)).toBe("ms.err.generic")
  })

  it("Fehlercode aus dem Kern-Client (err.code)", () => {
    expect(errorCode(Object.assign(new Error("x"), { code: "exists" }))).toBe("exists")
    expect(errorCode(new Error("x"))).toBeUndefined()
    expect(errorCode(null)).toBeUndefined()
  })

  it("private Microsoft-Adressen erkennen", () => {
    expect(looksMicrosoft("a@outlook.de")).toBe(true)
    expect(looksMicrosoft("a@hotmail.com")).toBe(true)
    expect(looksMicrosoft("a@gmx.de")).toBe(false)
    expect(looksMicrosoft("kaputt")).toBe(false)
  })
})
