import i18next from "i18next"
import { renderToStaticMarkup } from "react-dom/server"
import { I18nextProvider, initReactI18next } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }))

const { i18n: texts } = await import("./i18n")
const { CallSettings } = await import("./CallSettings")
const { CallList } = await import("./_CallList")
const { callTone, pendingTest, secondsLeft, shortTime } = await import("./callsLogic")
import type { CallEntry, Connection } from "./types"

const inst = i18next.createInstance()
beforeAll(async () => {
  await inst.use(initReactI18next).init({
    lng: "de", fallbackLng: "de", ns: ["voip"], defaultNS: "voip",
    resources: { de: { voip: texts.de.voip }, en: { voip: texts.en.voip } }, interpolation: { escapeValue: false },
  })
})
const html = (el: React.ReactElement) => renderToStaticMarkup(<I18nextProvider i18n={inst}>{el}</I18nextProvider>)

const CONN = {
  configured: true, has_password: true, enabled: true, status: "registered", status_at: null, created_at: "",
  updated_at: "u1", pbx: "fritzbox", display_name: "HydraHive", registrar: "192.168.3.1", registrar_port: 5060,
  username: "spike2000", own_number: "", local_sip_port: 5070, rtp_port_min: 7078, rtp_port_max: 7109,
  register_interval: 300, answer_calls: false, greeting: "", greeting_default: "Hallo, hier ist HydraHive.",
  test_until: null,
} as Extract<Connection, { configured: true }>

const call = (p: Partial<CallEntry>): CallEntry => ({
  id: 1, started_at: "2026-10-25T12:00:00+00:00", number: "•••981", result: "answered", codec: "PCMA",
  rtp_out: 250, rtp_in: 240, is_test: false, heard: null, ...p,
})

describe("Logik", () => {
  it("Restzeit Testfenster", () => {
    const now = Date.parse("2026-10-25T12:00:00Z")
    expect(secondsLeft("2026-10-25T12:00:30+00:00", now)).toBe(30)
    expect(secondsLeft("2026-10-25T11:59:00+00:00", now)).toBe(0)
    expect(secondsLeft(null, now)).toBe(0)
    expect(secondsLeft("kaputt", now)).toBe(0)
  })
  it("offener Testanruf: jüngster Test ohne Antwort, nicht besetzt", () => {
    expect(pendingTest([call({ id: 3, is_test: true }), call({ id: 2, is_test: true })])?.id).toBe(3)
    expect(pendingTest([call({ is_test: true, heard: true })])).toBeNull()
    expect(pendingTest([call({ is_test: false })])).toBeNull()
    expect(pendingTest([call({ is_test: true, result: "busy" })])).toBeNull()
  })
  it.each([["answered", "ok"], ["caller_hangup", "ok"], ["hung_up", "ok"], ["rejected", "idle"],
    ["cancelled", "idle"], ["no_ack", "warn"], ["codec", "warn"], ["busy", "warn"], ["no_port", "warn"]] as const)(
    "%s → %s", (r, tone) => expect(callTone(call({ result: r }))).toBe(tone))
  it("Zeit: heute nur Uhrzeit", () => {
    const now = new Date("2026-10-25T15:00:00")
    expect(shortTime("2026-10-25T13:05:00", now)).toMatch(/^13:05$/)
    expect(shortTime("2026-10-20T13:05:00", now)).toContain("20.10.")
    expect(shortTime("kaputt", now)).toBe("")
  })
})

describe("Karte Anrufe annehmen", () => {
  it("Schalter, Ansage mit Vorgabe, Testanruf-Knopf", () => {
    const h = html(<CallSettings conn={CONN} />)
    expect(h).toContain('data-voip-calls="1"')
    expect(h).toContain('role="switch"')
    expect(h).toContain('aria-checked="false"')
    expect(h).toContain('placeholder="Hallo, hier ist HydraHive."')
    expect(h).toContain('data-voip-test-call="1"')
    expect(h).toContain("Testanruf starten")
    expect(h).toMatch(/data-voip-test-call="1"(?![^>]*disabled)/)
  })
  it("Ansage-Knopf heißt „Ansage speichern“ und ist ohne Änderung gesperrt", () => {
    const h = html(<CallSettings conn={{ ...CONN, answer_calls: true }} />)
    expect(h).toContain("Ansage speichern")
    expect(h).toMatch(/<button[^>]*disabled=""[^>]*data-voip-calls-save="1"/)
    expect(h).toContain('aria-checked="true"')
  })
  it("ohne Verbindung: Testanruf gesperrt", () => {
    const h = html(<CallSettings conn={{ ...CONN, status: "disconnected" }} />)
    expect(h).toMatch(/<button[^>]*disabled=""[^>]*data-voip-test-call="1"/)
  })
  it("Liste: maskiert, Ergebnis, Test, Pakete", () => {
    const h = html(<CallList calls={[call({ is_test: true, heard: true }), call({ id: 2, result: "rejected", codec: "" })]} />)
    expect(h).toContain("•••981")
    expect(h).toContain("angenommen")
    expect(h).toContain("abgelehnt")
    expect(h).toContain("Ton gehört")
    expect(h).toContain("250 gesendet / 240 empfangen")
  })
  it("leere Liste", () => {
    expect(html(<CallList calls={[]} />)).toContain("Noch keine Anrufe.")
  })
  it("alle Ergebnisse haben Text (DE/EN)", () => {
    for (const r of ["answered", "rejected", "busy", "cancelled", "caller_hangup", "hung_up", "no_ack", "codec", "no_port"]) {
      expect(texts.de.voip.calls.result).toHaveProperty(r)
      expect(texts.en.voip.calls.result).toHaveProperty(r)
    }
  })
})
