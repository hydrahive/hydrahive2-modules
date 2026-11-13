// Bereich „HydraHive-App“ als statisches Markup (Muster DevicePanel.test.tsx).
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: { name?: string; n?: number }) => o?.name ? `${k}[${o.name}]` : o?.n !== undefined ? `${k}[${o.n}]` : k,
}) }))
import type { TvwAppCode, TvwAppDevice } from "./api"
import { AppDevicesPanel } from "./AppDevicesPanel"

const A = { onCode: vi.fn(), onRevoke: vi.fn(), onRemove: vi.fn(), onNotice: vi.fn() }
const NOW = new Date("2026-11-13T12:00:00Z")
const DEV: TvwAppDevice = { app_id: "a1", name: "Küche", device_id: "", kind: "tablet", model: "Galaxy Tab A",
  android: "9", app_version: "1.0", status: "active", remote_ip: "192.0.2.5", created_at: "",
  last_seen: "2026-11-13T11:59:30Z", state: {} }
const CODE: TvwAppCode = { code: "K7QM-2XPA", name: "Flur", expires_at: "2026-11-13T12:15:00Z",
  server: "https://192.0.2.1:8443", pin: "sha256/AbC=" }
const html = (devices: TvwAppDevice[], code: TvwAppCode | null = null, busy = false) =>
  renderToStaticMarkup(<AppDevicesPanel devices={devices} code={code} busy={busy} now={NOW} actions={A} />)

describe("TV-Werkstatt: Bereich HydraHive-App", () => {
  it("leer: Erklärung, Hinweis, Knopf Code erst mit Namen bedienbar", () => {
    const out = html([])
    for (const s of ["app.title", "app.explain", "app.none"]) expect(out).toContain(s)
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*>app\.new_code</)
  })

  it("Code wird groß gezeigt mit Restzeit, Server und Fingerabdruck", () => {
    const out = html([], CODE)
    for (const s of ["app.code_for[Flur]", "K7QM-2XPA", "app.code_valid[15]", "https://192.0.2.1:8443",
      "sha256/AbC=", "app.code_hint"]) expect(out).toContain(s)
  })

  it("ohne Fingerabdruck keine Fingerabdruck-Zeile", () => {
    expect(html([], { ...CODE, pin: null })).not.toContain("app.pin")
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
