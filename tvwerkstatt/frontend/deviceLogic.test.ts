import { describe, expect, it } from "vitest"
import type { TvwDevice, TvwJob } from "./api"
import {
  ACTION_STEPS, actionView, anyChecking, canInstall, checkView, kindKey, looksLikeAddress, ourHome,
} from "./deviceLogic"
import { tvwerkstattI18n } from "./i18n"
import { pollMs } from "./setupLogic"

const job = (state: string, step = "connect", error_code = ""): TvwJob => ({ job_id: "j", state, step, error_code,
  error_detail: "", started_by: "boss", created_at: "", updated_at: "" })
const dev = (p: Partial<TvwDevice> = {}): TvwDevice => ({ device_id: "d1", name: "Wohnzimmer", address: "192.0.2.10", ...p })

describe("TV-Werkstatt: Fernseher (Logik)", () => {
  it("checkView: prüft, wartet auf Freigabe, gescheitert, ruhig", () => {
    expect(checkView(dev())).toBe("idle")
    expect(checkView(dev({ check: job("running") }))).toBe("checking")
    expect(checkView(dev({ check: job("running", "authorize") }))).toBe("authorize")
    expect(checkView(dev({ check: job("failed", "connect", "tvw_adb_closed") }))).toBe("failed")
    expect(checkView(dev({ check: job("done", "done") }))).toBe("idle")
  })

  it("solange ein Fernseher geprüft wird, sieht die Seite öfter nach", () => {
    expect(anyChecking([dev(), dev({ check: job("running") })])).toBe(true)
    expect(anyChecking([dev({ check: job("done", "done") })])).toBe(false)
    expect(pollMs("ready", true)).toBe(2000)
    expect(pollMs("ready", false)).toBeNull()
  })

  it("Art nur, wenn sie gelesen wurde", () => {
    expect(kindKey("android_tv")).toBe("kind.android_tv")
    expect(kindKey("google_tv")).toBe("kind.google_tv")
    expect(kindKey("")).toBe("")
    expect(kindKey("irgendwas")).toBe("")
  })

  it("Adresse grob vorprüfen", () => {
    expect(looksLikeAddress("192.168.178.200")).toBe(true)
    expect(looksLikeAddress(" 192.168.178.200 ")).toBe(true)
    for (const a of ["", "192.168.178", "192.168.178.300", "fernseher.local", "1.2.3.4; ls"]) {
      expect(looksLikeAddress(a), a).toBe(false)
    }
  })

  it("unser Startbildschirm erkannt", () => {
    expect(ourHome(dev({ current_home: "com.gathin.tvhome" }))).toBe(true)
    expect(ourHome(dev({ current_home: "com.google.android.tvlauncher" }))).toBe(false)
  })

  it("actionView und Sperre während eines Auftrags am Fernseher", () => {
    expect(actionView(dev())).toBe("idle")
    expect(actionView(dev({ action: { ...job("running", "push"), kind: "install" } }))).toBe("installing")
    expect(actionView(dev({ action: { ...job("running", "restore"), kind: "restore" } }))).toBe("restoring")
    expect(actionView(dev({ action: { ...job("failed"), kind: "install" } }))).toBe("failed")
    expect(anyChecking([dev({ action: { ...job("running", "push"), kind: "install" } })])).toBe(true)
  })

  it("canInstall: Bau da, Debugging offen, Original bekannt", () => {
    const ok = dev({ adb_state: "open", stock_home: "com.google.android.tvlauncher" })
    expect(canInstall(ok, true)).toBe(true)
    expect(canInstall(ok, false)).toBe(false)
    expect(canInstall({ ...ok, adb_state: "unauthorized" }, true)).toBe(false)
    expect(canInstall({ ...ok, stock_home: "" }, true)).toBe(false)
  })

  it("jeder Schritt am Fernseher hat einen Text (de/en)", () => {
    for (const lang of ["de", "en"] as const) {
      const steps = tvwerkstattI18n[lang].tvwerkstatt.istep as Record<string, string>
      expect([...ACTION_STEPS, "restore"].filter((k) => !steps[k]), lang).toEqual([])
    }
  })
})
