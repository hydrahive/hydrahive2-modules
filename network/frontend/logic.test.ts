import { describe, expect, it } from "vitest"
import { chartPoints, dayRows, duration, errorKey, light, looksLikeUdmUrl, percentOfPlan, type Sample } from "./logic"

const t = (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k)

describe("Netzwerk – Hilfsfunktionen", () => {
  it("Fehlercodes", () => {
    expect(errorKey(Object.assign(new Error("x"), { code: "network_auth_failed" }))).toBe("err.network_auth_failed")
    expect(errorKey(Object.assign(new Error("x"), { code: "capability_denied" }))).toBe("err.network_configure_only")
    expect(errorKey(Object.assign(new Error("x"), { code: "irgendwas" }))).toBe("err.general")
    expect(errorKey("kaputt")).toBe("err.general")
    expect(errorKey(null)).toBe("err.general")
  })

  it("Dauer", () => {
    expect(duration(30660, t)).toBe('dur.hm:{"h":8,"m":31}')
    expect(duration(93600, t)).toBe('dur.dh:{"d":1,"h":2}')
    expect(duration(186, t)).toBe('dur.m:{"m":3}')
    expect(duration(21, t)).toBe('dur.s:{"s":21}')
    expect(duration(3600, t)).toBe('dur.hm:{"h":1,"m":0}')
    expect(duration(-5, t)).toBe('dur.s:{"s":0}')
  })

  it("Ampel", () => {
    expect(light(null, 10, 50)).toBe("unknown")
    expect(light(undefined, 10, 50)).toBe("unknown")
    expect(light(100, null, 50)).toBe("bad")
    expect(light(20, 10, 50)).toBe("warn")
    expect(light(0, 51, 50)).toBe("warn")
    expect(light(0, 50, 50)).toBe("ok")
    expect(light(0, null, 50)).toBe("ok")
  })

  it("Prozent vom Tarif", () => {
    expect(percentOfPlan(2, 50)).toBe(4)
    expect(percentOfPlan(947, 1000)).toBe(95)
    expect(percentOfPlan(null, 50)).toBeNull()
    expect(percentOfPlan(10, null)).toBeNull()
    expect(percentOfPlan(10, 0)).toBeNull()
  })

  it("Tage mit Störung, neueste zuerst", () => {
    expect(dayRows({ "2026-10-27": 30660, "2026-10-28": 38000, "2026-10-26": 0 })).toEqual([
      { day: "2026-10-28", seconds: 38000 }, { day: "2026-10-27", seconds: 30660 }])
  })

  it("Diagramm-Punkte", () => {
    const s = { ts: 60, inet_rtt_avg: 12, inet_loss: null, path: "cable" } as unknown as Sample
    expect(chartPoints([s])).toEqual([{ ts: 60, rtt: 12, loss: 0, path: "cable" }])
  })

  it("Adresse der Dream Machine", () => {
    expect(looksLikeUdmUrl("https://192.168.178.1")).toBe(true)
    expect(looksLikeUdmUrl(" https://unifi.local:8443/ ")).toBe(true)
    expect(looksLikeUdmUrl("http://192.168.178.1")).toBe(false)
    expect(looksLikeUdmUrl("https://192.168.178.1/pfad")).toBe(false)
    expect(looksLikeUdmUrl("")).toBe(false)
  })
})
