import i18next from "i18next"
import { renderToStaticMarkup } from "react-dom/server"
import { I18nextProvider, initReactI18next } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }))

const { i18n: texts } = await import("./i18n")
const { DialPanel } = await import("./DialPanel")
const { CallList } = await import("./_CallList")
const { dialErrorKey, dialStateKey, cleanNumberInput } = await import("./dialLogic")
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
  username: "hydra-telefon", own_number: "", local_sip_port: 5070, rtp_port_min: 7078, rtp_port_max: 7109,
  register_interval: 300, answer_calls: false, greeting: "", greeting_default: "Hallo.", test_until: null,
  call_mode: "greeting", assistant_name: "", assistant_knowledge: "", assistant_model: "",
  allow_premium: false, allow_foreign: false,
} as Extract<Connection, { configured: true }>

describe("Logik Anrufen", () => {
  it("Fehlercodes der API → Texte", () => {
    for (const code of ["number_emergency", "number_premium", "number_foreign", "number_invalid",
      "number_no_area_code", "not_registered", "line_busy", "too_fast", "daily_limit"]) {
      const key = dialErrorKey(code)
      expect(key).toBe(`dial.error.${code}`)
      expect(inst.t(key)).not.toBe(key)
      expect(inst.t(key, { lng: "en" })).not.toBe(key)
    }
    expect(dialErrorKey(undefined)).toBe("dial.error.unknown")
    expect(dialErrorKey("irgendwas")).toBe("dial.error.unknown")
  })
  it("Zustände → Texte", () => {
    for (const s of ["calling", "ringing", "answered", "ended"]) {
      expect(inst.t(dialStateKey(s))).not.toBe(dialStateKey(s))
    }
    expect(dialStateKey("kaputt")).toBe("dial.state.calling")
  })
  it("Eingabe: nur Ziffern und Trennzeichen, höchstens 40", () => {
    expect(cleanNumberInput("030 123-45/67 (x)")).toBe("030 123-45/67 ()")
    expect(cleanNumberInput("+49 30")).toBe("+49 30")
    expect(cleanNumberInput("**610#")).toBe("610")
    expect(cleanNumberInput("1".repeat(50)).length).toBe(40)
  })
})

describe("Oberfläche Anrufen", () => {
  it("Formular mit Nummer, Ansage, Anrufen-Knopf und Hinweisen", () => {
    const h = html(<DialPanel conn={CONN} />)
    expect(h).toContain('data-voip-dial-number="1"')
    expect(h).toContain('data-voip-dial-text="1"')
    expect(h).toContain('data-voip-dial-start="1"')
    expect(h).toContain("Anrufen &amp; Ansage vorlesen")
    expect(h).toContain("Notrufnummern")
    expect(h).toContain("20")
  })
  const startDisabled = (h: string) => /<button[^>]*data-voip-dial-start="1"[^>]*disabled=""|<button[^>]*disabled=""[^>]*data-voip-dial-start="1"/.test(h)
  it("Nicht verbunden → Hinweis, Knopf aus (auch mit Nummer)", () => {
    const h = html(<DialPanel conn={{ ...CONN, status: "disconnected" }} initialNumber="030 1234567" />)
    expect(h).toContain('data-voip-dial-needs-connection="1"')
    expect(startDisabled(h)).toBe(true)
  })
  it("Verbunden mit Nummer → Knopf an; ohne Nummer → aus", () => {
    expect(startDisabled(html(<DialPanel conn={CONN} initialNumber="030 1234567" />))).toBe(false)
    expect(startDisabled(html(<DialPanel conn={CONN} />))).toBe(true)
  })
  it("Freigaben für Sondernummern und Ausland als Schalter, Standard aus", () => {
    const h = html(<DialPanel conn={CONN} />)
    expect(h).toContain('data-voip-allow="premium"')
    expect(h).toContain('data-voip-allow="foreign"')
    expect((h.match(/data-voip-switch="off"/g) ?? []).length).toBeGreaterThanOrEqual(2)
  })
  it("Anrufliste zeigt die Richtung", () => {
    const c = (p: Partial<CallEntry>): CallEntry => ({
      id: 1, started_at: "2026-10-25T12:00:00+00:00", number: "•••567", result: "answered", codec: "PCMA",
      rtp_out: 1, rtp_in: 1, is_test: false, heard: null, turns: 0, notes: {}, notes_read: true, direction: "in", kind: "greeting", ...p,
    })
    const h = html(<CallList calls={[c({ id: 1, direction: "out" }), c({ id: 2, direction: "in" })]} />)
    expect(h).toContain('data-voip-direction="out"')
    expect(h).toContain('data-voip-direction="in"')
  })
  it("Ergebnisse ausgehender Anrufe haben Texte", () => {
    for (const r of ["no_answer", "declined", "invalid_number", "failed", "auth_failed", "unreachable", "remote_hangup"]) {
      expect(inst.t(`calls.result.${r}`)).not.toBe(`calls.result.${r}`)
      expect(inst.t(`calls.result.${r}`, { lng: "en" })).not.toBe(`calls.result.${r}`)
    }
  })
})

describe("Anrufen mit Assistent (3b)", () => {
  it("Auswahl Ansage/Assistent, Standard Ansage", () => {
    const h = html(<DialPanel conn={CONN} />)
    expect(h).toContain('data-voip-dial-mode="greeting"')
    expect(h).toContain('data-voip-dial-mode="assistant"')
    expect(h).not.toContain('data-voip-dial-task="1"')
  })
  it("Assistent: Felder Auftrag und Darf nennen, keine Ansage", () => {
    const h = html(<DialPanel conn={CONN} initialMode="assistant" initialTask="Frag nach einem Termin." />)
    expect(h).toContain('data-voip-dial-task="1"')
    expect(h).toContain('data-voip-dial-share="1"')
    expect(h).not.toContain('data-voip-dial-text="1"')
    expect(h).toContain("Frag nach einem Termin.")
    expect(h).toContain("keine Zusagen")
  })
  it("Assistent ohne Auftrag → Knopf aus", () => {
    const off = html(<DialPanel conn={CONN} initialMode="assistant" initialNumber="030 1234567" />)
    const on = html(<DialPanel conn={CONN} initialMode="assistant" initialNumber="030 1234567" initialTask="Frag nach." />)
    const dis = (h: string) => /<button[^>]*data-voip-dial-start="1"[^>]*disabled=""|<button[^>]*disabled=""[^>]*data-voip-dial-start="1"/.test(h)
    expect(dis(off)).toBe(true)
    expect(dis(on)).toBe(false)
  })
  it("Fehler task_required hat einen Text", () => {
    expect(dialErrorKey("task_required")).toBe("dial.error.task_required")
    expect(inst.t("dial.error.task_required")).not.toBe("dial.error.task_required")
  })
  it("Notiz: Ergebnis wird angezeigt, Zurückrufen nur mit Nummer", () => {
    const c = (p: Partial<CallEntry>): CallEntry => ({
      id: 1, started_at: "2026-10-25T12:00:00+00:00", number: "•••567", result: "assistant_end", codec: "PCMA",
      rtp_out: 1, rtp_in: 1, is_test: false, heard: null, turns: 2, notes: {}, notes_read: true, direction: "in", kind: "greeting", ...p,
    })
    const h = html(<CallList calls={[
      c({ id: 1, direction: "out", notes: { result: "Termin Di 10 Uhr möglich, nicht gebucht." } }),
      c({ id: 2, notes: { name: "Erika Musterfrau", callback_number: "030 1234567" } }),
      c({ id: 3, notes: { name: "Ohne Nummer" } }),
    ]} onCallback={() => undefined} />)
    expect(h).toContain("Termin Di 10 Uhr möglich, nicht gebucht.")
    expect(h).toContain('data-voip-result="1"')
    expect((h.match(/data-voip-callback="/g) ?? []).length).toBe(1)
    expect(h).toContain('data-voip-callback="2"')
  })
  it("Ohne onCallback kein Knopf", () => {
    const h = html(<CallList calls={[{
      id: 2, started_at: "2026-10-25T12:00:00+00:00", number: "•••567", result: "assistant_end", codec: "PCMA",
      rtp_out: 1, rtp_in: 1, is_test: false, heard: null, turns: 2, notes: { callback_number: "030 1234567" },
      notes_read: true, direction: "in", kind: "assistant",
    }]} />)
    expect(h).not.toContain("data-voip-callback")
  })
  it("Abschnitt der Anrufliste im Reiter Telefonaufträge", () => {
    const h = html(<DialPanel conn={CONN} />)
    expect(h).toContain('data-voip-dial-calls="1"')
  })
})

describe("Anrufart sichtbar (Till 25.10.)", () => {
  const c = (p: Partial<CallEntry>): CallEntry => ({
    id: 1, started_at: "2026-10-25T12:00:00+00:00", number: "•••567", result: "answered", codec: "PCMA",
    rtp_out: 1, rtp_in: 1, is_test: false, heard: null, turns: 0, notes: {}, notes_read: true, direction: "out",
    kind: "greeting", ...p,
  })
  it("Liste zeigt Ansage bzw. Assistent als Text", () => {
    const h = html(<CallList calls={[c({ id: 1, kind: "greeting" }), c({ id: 2, kind: "assistant", result: "assistant_end" }),
      c({ id: 3, kind: "", result: "rejected" })]} />)
    expect(h).toContain('data-voip-kind="greeting"')
    expect(h).toContain('data-voip-kind="assistant"')
    expect((h.match(/data-voip-kind=/g) ?? []).length).toBe(2)
    expect(h).toContain(">Ansage<")
    expect(h).toContain(">Assistent<")
  })
  it("Auswahl als zwei große Karten mit Erklärung", () => {
    const h = html(<DialPanel conn={CONN} />)
    expect(h).toContain('role="radiogroup"')
    expect((h.match(/role="radio"/g) ?? []).length).toBe(2)
    expect(h).toMatch(/data-voip-dial-mode="greeting"[^>]*aria-checked="true"|aria-checked="true"[^>]*data-voip-dial-mode="greeting"/)
    expect(h).toContain("liest deinen Text vor und legt auf")
    expect(h).toContain("führt ein Gespräch mit deinem Auftrag")
  })
  it("Knopf sagt, was passiert", () => {
    expect(html(<DialPanel conn={CONN} />)).toContain("Anrufen &amp; Ansage vorlesen")
    expect(html(<DialPanel conn={CONN} initialMode="assistant" />)).toContain("Anrufen mit Assistent")
  })
})
