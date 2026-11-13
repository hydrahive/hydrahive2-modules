// Bereich „HydraHive-App“ als statisches Markup (Muster DevicePanel.test.tsx).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: { name?: string; n?: number }) => o?.name ? `${k}[${o.name}]` : o?.n !== undefined ? `${k}[${o.n}]` : k,
}) }))
import type { TvwAppApk, TvwAppCode, TvwAppDevice, TvwJob } from "./api"
import { AppDevicesPanel } from "./AppDevicesPanel"

const A = { onCode: vi.fn(), onRevoke: vi.fn(), onRemove: vi.fn(), onNotice: vi.fn(), onBuild: vi.fn(), onDownload: vi.fn() }
const NOW = new Date("2026-11-13T12:00:00Z")
const DEV: TvwAppDevice = { app_id: "a1", name: "Küche", device_id: "", kind: "tablet", model: "Galaxy Tab A",
  android: "9", app_version: "1.0", status: "active", remote_ip: "192.0.2.5", created_at: "",
  last_seen: "2026-11-13T11:59:30Z", state: {} }
const CODE: TvwAppCode = { code: "K7QM-2XPA", name: "Flur", expires_at: "2026-11-13T12:15:00Z",
  server: "https://192.0.2.1:8443", pin: "sha256/AbC=", pin_short: "3FA2 91C0 7B1E" }
const APK: TvwAppApk = { version: "0.1.0 (1)", size: 20332, sha256: "7ce69f976b834d3b" + "0".repeat(48), created_at: "" }
const job = (state: string, step = "build", error_code = ""): TvwJob => ({ job_id: "j", state, step, error_code,
  error_detail: "", started_by: "boss", created_at: "", updated_at: "" })
const html = (devices: TvwAppDevice[], code: TvwAppCode | null = null, busy = false,
  extra: { build?: TvwJob | null; apk?: TvwAppApk | null; ready?: boolean } = {}) =>
  renderToStaticMarkup(<AppDevicesPanel data={{ devices, build: extra.build ?? null, apk: extra.apk ?? null }}
    code={code} ready={extra.ready ?? true} busy={busy} now={NOW} actions={A} />)

describe("TV-Werkstatt: Bereich HydraHive-App", () => {
  it("leer: Erklärung, Hinweis, Knopf Code erst mit Namen bedienbar", () => {
    const out = html([])
    for (const s of ["app.title", "app.explain", "app.none"]) expect(out).toContain(s)
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*>app\.new_code</)
  })

  it("Code wird groß gezeigt mit Restzeit, Server und kurzem Fingerabdruck zum Vergleichen", () => {
    const out = html([], CODE)
    for (const s of ["app.code_for[Flur]", "K7QM-2XPA", "app.code_valid[15]", "https://192.0.2.1:8443",
      "3FA2 91C0 7B1E", "app.code_hint_pin"]) expect(out).toContain(s)
    expect(out).not.toContain("sha256/AbC=")                    // der lange Pin ist nur für Technik, nicht zum Lesen
  })

  it("ohne Fingerabdruck (öffentliche Adresse) keine Fingerabdruck-Zeile", () => {
    const out = html([], { ...CODE, pin: null, pin_short: null })
    expect(out).not.toContain("app.pin")
    expect(out).toContain("app.code_hint")
    expect(out).not.toContain("app.code_hint_pin")
  })

  it("Pin ohne Kurzform: keine Fingerabdruck-Zeile (die App zeigt nur die Kurzform)", () => {
    const out = html([], { ...CODE, pin_short: null })
    expect(out).not.toContain("app.pin")
    expect(out).not.toContain("app.code_hint_pin")
  })

  it("noch nie gebaut: Knopf App bauen, kein Herunterladen", () => {
    const out = html([])
    expect(out).toContain("app.build_none")
    expect(out).toMatch(/<button[^>]*>app\.build</)
    expect(out).not.toContain("app.download")
  })

  it("ohne eingerichtete Werkstatt: Bauen gesperrt mit Hinweis", () => {
    const out = html([], null, false, { ready: false })
    expect(out).toContain("app.build_need_setup")
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*>app\.build</)
  })

  it("Bau läuft: Schritt n von m mit Namen, Bauen gesperrt", () => {
    const out = html([], null, false, { build: job("running", "unpack") })
    expect(out).toContain("app.build_running[4]")
    expect(out).toContain("app.bstep.unpack")
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*>app\.build</)
  })

  it("gebaut: Version, Größe, Prüfsumme, Herunterladen mit Hinweis, Neu bauen", () => {
    const out = html([], null, false, { apk: APK, build: job("done", "") })
    for (const s of ["app.built", "20 KB", "build.hash", "app.download", "app.download_hint",
      "app.build_again"]) expect(out).toContain(s)
  })

  it("Bau gescheitert: Fehlertext, alte App bleibt herunterladbar", () => {
    const out = html([], null, false, { apk: APK, build: job("failed", "build", "tvw_app_build_tests") })
    expect(out).toContain("err.tvw_app_build_tests")
    expect(out).toContain("app.download")
  })

  it("aktives Gerät: verbunden, Testmeldung, Sperren; kein Entfernen", () => {
    const out = html([DEV])
    for (const s of ["Küche", "Tablet · Galaxy Tab A · Android 9 · App 1.0", "app.online", "app.notice_ph",
      "app.send", "app.revoke"]) expect(out).toContain(s)
    expect(out).not.toContain("app.remove")
    expect(out).not.toContain("app.none")
  })

  it("lange still: nicht verbunden", () => {
    expect(html([{ ...DEV, last_seen: "2026-11-13T11:50:00Z" }])).toContain("app.offline")
  })

  it("gesperrt: Entfernen statt Sperren, keine Testmeldung", () => {
    const out = html([{ ...DEV, status: "revoked" }])
    expect(out).toContain("app.revoked")
    expect(out).toContain("app.remove")
    expect(out).not.toContain(">app.revoke<")
    expect(out).not.toContain("app.notice_ph")
  })

  it("beschäftigt: Sperren gesperrt", () => {
    expect(html([DEV], null, true)).toMatch(/<button[^>]*disabled=""[^>]*>app\.revoke</)
  })
})
