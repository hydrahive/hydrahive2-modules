import i18next from "i18next"
import { renderToStaticMarkup } from "react-dom/server"
import { I18nextProvider, initReactI18next } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }))

const { i18n: texts } = await import("./i18n")
const { CallSettings } = await import("./CallSettings")
const { CallList } = await import("./_CallList")
const { assistantDirty, callTone, hasNote, noteLine, pendingTest, secondsLeft, shortTime } = await import("./callsLogic")
const { AssistantFields } = await import("./_AssistantFields")
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
  test_until: null, call_mode: "greeting", assistant_name: "", assistant_knowledge: "", assistant_model: "",
} as Extract<Connection, { configured: true }>

const call = (p: Partial<CallEntry>): CallEntry => ({
  id: 1, started_at: "2026-10-25T12:00:00+00:00", number: "•••981", result: "answered", codec: "PCMA",
  rtp_out: 250, rtp_in: 240, is_test: false, heard: null, turns: 0, notes: {}, notes_read: true, ...p,
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
    for (const r of ["answered", "rejected", "busy", "cancelled", "caller_hangup", "hung_up", "no_ack", "codec", "no_port",
      "assistant_end", "no_input", "max_duration", "errors"]) {
      expect(texts.de.voip.calls.result).toHaveProperty(r)
      expect(texts.en.voip.calls.result).toHaveProperty(r)
    }
  })
})

describe("Telefon-Assistent", () => {
  const A = { mode: "assistant" as const, assistant_name: "Beispiel GmbH", assistant_knowledge: "Mo–Fr 9–17", assistant_model: "" }

  it("Modus Nur Ansage: Wissensfeld unsichtbar, Ansage sichtbar", () => {
    const h = html(<CallSettings conn={CONN} />)
    expect(h).toContain('data-voip-mode="greeting"')
    expect(h).not.toContain('data-voip-assistant-knowledge="1"')
    expect(h).toContain('data-voip-greeting="1"')
  })
  it("Modus Assistent: Name, Wissen, Modell, Rechte-Hinweis; keine Ansage", () => {
    const h = html(<CallSettings conn={{ ...CONN, call_mode: "assistant", assistant_name: "Beispiel GmbH" }} />)
    expect(h).toContain('data-voip-assistant-name="1"')
    expect(h).toContain('value="Beispiel GmbH"')
    expect(h).toContain('data-voip-assistant-knowledge="1"')
    expect(h).toContain('data-voip-assistant-model="1"')
    expect(h).toContain("Anrufer sind Fremde")
    expect(h).not.toContain('data-voip-greeting="1"')
  })
  it("Speichern-Knopf erst bei Änderung", () => {
    const h = html(<AssistantFields saved={A} busy={false} onSave={async () => {}} />)
    expect(h).toMatch(/<button[^>]*disabled=""[^>]*data-voip-assistant-save="1"/)
    expect(assistantDirty({ ...A, assistant_name: " Beispiel GmbH " }, A)).toBe(false)
    expect(assistantDirty({ ...A, mode: "greeting" }, A)).toBe(true)
    expect(assistantDirty({ ...A, assistant_model: "x" }, A)).toBe(true)
  })
  it("Platzhalter neutral", () => {
    expect(texts.de.voip.assistant.name_placeholder).toContain("Max Mustermann")
    expect(texts.en.voip.assistant.name_placeholder).toContain("Jane Doe")
  })
})

describe("Notizen", () => {
  const note = { name: "Max Mustermann", concern: "Angebot", callback_wanted: true, callback_number: "0123 456789",
    summary: "Möchte ein Angebot.", open_questions: ["Preis?"], needs_review: true }

  it("Zeile: Name · Anliegen · Rückruf", () => {
    expect(noteLine(note)).toBe("Max Mustermann · Angebot · Rückruf 0123 456789")
    expect(noteLine({ name: "A" })).toBe("A")
    expect(noteLine({ callback_wanted: true })).toBe("Rückruf")
    expect(hasNote(call({ notes: {} }))).toBe(false)
  })
  it("Liste zeigt Notiz, neu-Markierung und Knopf", () => {
    const h = html(<CallList calls={[call({ result: "assistant_end", turns: 3, notes: note, notes_read: false })]} onRead={() => {}} />)
    expect(h).toContain('data-voip-note="1"')
    expect(h).toContain("Max Mustermann · Angebot · Rückruf 0123 456789")
    expect(h).toContain("Möchte ein Angebot.")
    expect(h).toContain("Preis?")
    expect(h).toContain("Bitte ansehen")
    expect(h).toContain('data-voip-unread="1"')
    expect(h).toContain('data-voip-mark-read="1"')
    expect(h).toContain("Gespräch mit dem Assistenten")
  })
  it("gelesene Notiz ohne Knopf", () => {
    const h = html(<CallList calls={[call({ notes: note, notes_read: true })]} onRead={() => {}} />)
    expect(h).not.toContain('data-voip-mark-read="1"')
    expect(h).not.toContain('data-voip-unread="1"')
  })
})
