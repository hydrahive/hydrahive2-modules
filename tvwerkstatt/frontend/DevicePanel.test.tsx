// Bereich „Fernseher“ als statisches Markup (Muster SetupPanel.test.tsx).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import type { TvwDevice, TvwJob } from "./api"
import { DevicePanel } from "./DevicePanel"

const A = { onAdd: vi.fn(), onCheck: vi.fn(), onRemove: vi.fn() }
const job = (state: string, step = "connect", error_code = ""): TvwJob => ({ job_id: "j", state, step, error_code,
  error_detail: "", started_by: "boss", created_at: "", updated_at: "" })
const SONY: TvwDevice = { device_id: "d1", name: "Wohnzimmer", address: "192.0.2.10", model: "Sony BRAVIA 4K UR3",
  android: "9", kind: "android_tv", adb_state: "open", current_home: "com.gathin.tvhome" }
const html = (devices: TvwDevice[], ready = true, busy = false) =>
  renderToStaticMarkup(<DevicePanel devices={devices} ready={ready} busy={busy} actions={A} />)

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
})
