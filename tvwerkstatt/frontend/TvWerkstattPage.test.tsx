// Die Seite als statisches Markup (Muster telephony/studio): Zustand rein, Text raus. Laden steckt im Hook.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "" }) } }))
import type { TvwDesktop, TvwState } from "./api"
import { DEFAULT_LOOK } from "./testLook"
import type { Tab } from "./tabs"
import { PageView } from "./TvWerkstattPage"

const NOOP = {
  onLook: () => {}, onSave: () => {}, onReadApps: () => {}, onPushLook: () => {}, onBuild: () => {}, onInstall: () => {},
  onRestore: () => {}, onMood: () => {}, onUpload: () => {}, onDeleteWall: () => {},
}
const LEER: TvwState = { incus: true, error_code: "", devices: [], builds: [], container: "stopped", setup: null }
const SONY = { device_id: "d1", name: "Wohnzimmer", address: "192.0.2.10", model: "Sony BRAVIA 4K GB ATV3",
  android: "9", kind: "android_tv", adb_state: "open", current_home: "com.gathin.tvhome",
  stock_home: "com.google.android.tvlauncher" }
const DESK: TvwDesktop = { look: DEFAULT_LOOK, apps: [{ package: "com.netflix.ninja", label: "Netflix", version: "1",
  has_banner: 1, color: "" }], wallpapers: [], pushed_at: "", pushed_current: false, read_job: null, push_job: null }
const html = (s: TvwState | null, tab: Tab = "desktop", msg: string | null = null) => renderToStaticMarkup(
  <PageView s={s} msg={msg} tab={tab} deviceId="d1" desk={DESK} draft={DEFAULT_LOOK} mood="evening"
    now={new Date(2026, 10, 13, 20, 14)} desktop={NOOP} />)

describe("TV-Werkstatt: Seite", () => {
  it("ohne Container-Umgebung eine verständliche Meldung, keine Reiter", () => {
    const out = html({ ...LEER, incus: false, error_code: "tvw_no_incus" })
    expect(out).toContain("err.tvw_no_incus")
    expect(out).not.toContain('role="tablist"')
  })

  it("Reiter wie die Demo, in dieser Reihenfolge", () => {
    const out = html(LEER)
    const pos = ["tab.desktop", "tab.debloat", "tab.addons", "tab.devices", "tab.build"].map((k) => out.indexOf(k))
    expect(pos.every((p) => p >= 0)).toBe(true)
    expect([...pos].sort((a, b) => a - b)).toEqual(pos)
  })

  it("Desktop ohne Fernseher: Hinweis, zuerst einen einzutragen", () => {
    expect(html(LEER)).toContain("desk.need_device")
  })

  it("Desktop ohne eingerichtete Werkstatt: Hinweis zur Bauumgebung", () => {
    expect(html({ ...LEER, container: "missing", devices: [SONY] })).toContain("desk.need_setup")
  })

  it("Desktop mit Fernseher: drei Spalten wie die Demo – Gerät, Vorschau mit Schritten, Aussehen", () => {
    const out = html({ ...LEER, devices: [SONY] })
    for (const k of ["desk.device", "Sony BRAVIA 4K GB ATV3", "desk.on_tv", 'data-testid="tv"', "20:14", "desk.step_build",
      "desk.step_install", "desk.push_look", "install.restore", "desk.look", "desk.columns", "desk.dock_title"]) {
      expect(out, k).toContain(k)
    }
    expect(out).toContain("Wohnzimmer · 192.0.2.10")
  })

  it("Reiter Geräte: Liste und Formular", () => {
    const out = html({ ...LEER, devices: [SONY] }, "devices")
    expect(out).toContain("Wohnzimmer")
    expect(out).toContain("device.add_title")
  })

  it("Reiter Bauumgebung: Einrichten und Startbildschirm", () => {
    const out = html(LEER, "build")
    expect(out).toContain("setup.title")
    expect(out).toContain("build.title")
  })

  it("Entrümpeln: ohne Fernseher Hinweis, mit Fernseher der echte Reiter (kein Platzhalter mehr)", () => {
    expect(html(LEER, "debloat")).toContain("desk.need_device")
    const tv = { device_id: "t1", name: "Wohnzimmer", address: "192.0.2.11" }
    const out = renderToStaticMarkup(<PageView s={{ ...LEER, devices: [tv] }} msg={null} tab="debloat" deviceId="t1" />)
    expect(out).toContain("deb.read")
    expect(out).not.toContain("debloat_soon")
  })

  it("Zusätze sagen noch, was kommt", () => {
    expect(html(LEER, "addons")).toContain("tab.addons_soon")
  })

  it("Fehler beim Laden: Text zum Code", () => {
    const out = html(null, "desktop", "err.general")
    expect(out).toContain("err.general")
    expect(out).toContain('role="alert"')
  })
})
