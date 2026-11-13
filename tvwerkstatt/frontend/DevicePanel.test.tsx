// Bereich „Fernseher“ als statisches Markup (Muster SetupPanel.test.tsx).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: { step?: string }) => o?.step ? `${k}[${o.step}]` : k,
}) }))
import type { TvwDevice, TvwJob } from "./api"
import { DevicePanel } from "./DevicePanel"

const A = { onAdd: vi.fn(), onCheck: vi.fn(), onRemove: vi.fn(), onInstall: vi.fn(), onRestore: vi.fn() }
const job = (state: string, step = "connect", error_code = ""): TvwJob => ({ job_id: "j", state, step, error_code,
  error_detail: "", started_by: "boss", created_at: "", updated_at: "" })
const SONY: TvwDevice = { device_id: "d1", name: "Wohnzimmer", address: "192.0.2.10", model: "Sony BRAVIA 4K UR3",
  android: "9", kind: "android_tv", adb_state: "open", current_home: "com.gathin.tvhome",
  stock_home: "com.google.android.tvlauncher" }
const html = (devices: TvwDevice[], ready = true, busy = false, hasBuild = true) =>
  renderToStaticMarkup(<DevicePanel devices={devices} ready={ready} busy={busy} hasBuild={hasBuild} actions={A} />)
const STOCK = { ...SONY, current_home: "com.google.android.tvlauncher", stock_home: "com.google.android.tvlauncher" }

describe("TV-Werkstatt: Bereich Fernseher", () => {
  it("nicht eingerichtet: Hinweis statt Formular", () => {
    const out = html([], false)
    expect(out).toContain("device.need_setup")
    expect(out).not.toContain("device.add_title")
  })

  it("eingerichtet, leer: Formular mit Name und Adresse, Knopf erst nach Eingabe bedienbar", () => {
    const out = html([])
    expect(out).toContain("no_devices")
    expect(out).toContain("device.add_explain")
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*>device\.add</)
  })

  it("geprüfter Fernseher: Modell, Android, Art, Adresse, Zustand, unser Startbildschirm", () => {
    const out = html([SONY])
    for (const s of ["Wohnzimmer", "Sony BRAVIA 4K UR3 · Android 9 · kind.android_tv", "192.0.2.10", "adb.open",
      "device.our_home", "device.check", "device.remove"]) expect(out).toContain(s)
  })

  it("wartet auf Freigabe: deutlicher Hinweis, keine Knöpfe", () => {
    const out = html([{ ...SONY, check: job("running", "authorize") }])
    expect(out).toContain("device.authorize")
    expect(out).not.toContain("device.check<")
    expect(out).not.toContain("device.remove<")
  })

  it("gescheitert: Text zum Fehler und Erneut prüfen", () => {
    const out = html([{ ...SONY, adb_state: "unauthorized", check: job("failed", "connect", "tvw_adb_unauthorized") }])
    expect(out).toContain("err.tvw_adb_unauthorized")
    expect(out).toContain("adb.unauthorized")
    expect(out).toContain("device.check")
  })

  it("Original ist Home: Knopf aufspielen, kein Zurück", () => {
    const out = html([STOCK])
    expect(out).toContain("install.start")
    expect(out).not.toContain("install.restore<")
    expect(out).not.toMatch(/<button[^>]*disabled=""[^>]*>install\.start/)
  })

  it("unser Startbildschirm ist Home: Zurück zum Original, kein Aufspielen", () => {
    const out = html([SONY])
    expect(out).toContain("install.restore")
    expect(out).not.toContain("install.start")
  })

  it("ohne Bau: Aufspielen gesperrt und Hinweis", () => {
    const out = html([STOCK], true, false, false)
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*>install\.start/)
    expect(out).toContain("install.need_build")
  })

  it("Debugging zu oder Original unbekannt: Aufspielen gesperrt", () => {
    expect(html([{ ...STOCK, adb_state: "closed" }])).toMatch(/<button[^>]*disabled=""[^>]*>install\.start/)
    expect(html([{ ...STOCK, stock_home: "" }])).toMatch(/<button[^>]*disabled=""[^>]*>install\.start/)
  })

  it("wird aufgespielt: Schritt sichtbar, keine Knöpfe", () => {
    const out = html([{ ...STOCK, action: { ...job("running", "push"), kind: "install" } }])
    expect(out).toContain("install.running[istep.push]")
    expect(out).not.toContain("install.start<")
    expect(out).not.toContain("device.remove<")
  })

  it("Aufspielen gescheitert: Text zum Fehler", () => {
    const out = html([{ ...STOCK, action: { ...job("failed", "restore", "tvw_home_not_switched"), kind: "install" } }])
    expect(out).toContain("err.tvw_home_not_switched")
  })
})
