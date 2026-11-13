// Reine Logik der App-Geräte.
import { describe, expect, it } from "vitest"
import type { TvwAppDevice, TvwJob } from "./api"
import { app as de } from "./i18n.app.de"
import { app as en } from "./i18n.app.en"
import { APP_BUILD_STEPS, appBuildStep, appBuildView, appLine, buttonsOf, minutesLeft, online } from "./appLogic"

const NOW = new Date("2026-11-13T12:00:00Z")
const DEV: TvwAppDevice = { app_id: "a1", name: "Küche", device_id: "", kind: "tablet", model: "Galaxy Tab A",
  android: "9", app_version: "1.0", status: "active", remote_ip: "192.0.2.5", created_at: "",
  last_seen: "2026-11-13T11:59:00Z", state: {} }

describe("TV-Werkstatt: App-Logik", () => {
  it("online nur aktiv und Lebenszeichen höchstens 90 s alt", () => {
    expect(online(DEV, NOW)).toBe(true)
    expect(online({ ...DEV, last_seen: "2026-11-13T11:58:29Z" }, NOW)).toBe(false)
    expect(online({ ...DEV, last_seen: "2026-11-13T11:58:30Z" }, NOW)).toBe(true)
    expect(online({ ...DEV, status: "revoked" }, NOW)).toBe(false)
    expect(online({ ...DEV, last_seen: "" }, NOW)).toBe(false)
    expect(online({ ...DEV, last_seen: "kaputt" }, NOW)).toBe(false)
  })

  it("Zeile mit Art, Modell, Android, App; leere Teile fallen weg", () => {
    expect(appLine(DEV)).toBe("Tablet · Galaxy Tab A · Android 9 · App 1.0")
    expect(appLine({ ...DEV, kind: "tv", model: "", app_version: "" })).toBe("TV · Android 9")
    expect(appLine({ ...DEV, kind: "", model: "", android: "", app_version: "" })).toBe("")
  })

  it("Knöpfe: höchstens 3, je 20 Zeichen, leere weg", () => {
    expect(buttonsOf("Ansehen, Später")).toEqual(["Ansehen", "Später"])
    expect(buttonsOf(" , a,,b ,c,d")).toEqual(["a", "b", "c"])
    expect(buttonsOf("x".repeat(25))).toEqual(["x".repeat(20)])
    expect(buttonsOf("")).toEqual([])
  })

  it("Restminuten abgerundet, nie negativ", () => {
    expect(minutesLeft("2026-11-13T12:14:59Z", NOW)).toBe(14)
    expect(minutesLeft("2026-11-13T11:00:00Z", NOW)).toBe(0)
    expect(minutesLeft("kaputt", NOW)).toBe(0)
  })

  it("Bau-Schritte wie im Backend, jeder mit Text de/en", () => {
    expect([...APP_BUILD_STEPS]).toEqual(["container", "fetch", "verify", "unpack", "build", "collect"])
    expect(appBuildStep("unpack")).toEqual({ n: 4, total: 6 })
    expect(appBuildStep("quatsch")).toEqual({ n: 0, total: 6 })
    for (const [lang, t] of [["de", de], ["en", en]] as const)
      expect(APP_BUILD_STEPS.filter((k) => !(t.bstep as Record<string, string>)[k]), lang).toEqual([])
  })

  it("Bau-Zustand: laufend und gescheitert gehen vor, sonst fertig nur mit App", () => {
    const j = (state: string) => ({ state } as TvwJob)
    expect(appBuildView(j("running"), true)).toBe("running")
    expect(appBuildView(j("failed"), true)).toBe("failed")
    expect(appBuildView(j("done"), true)).toBe("done")
    expect(appBuildView(j("done"), false)).toBe("none")
    expect(appBuildView(null, false)).toBe("none")
  })
})
