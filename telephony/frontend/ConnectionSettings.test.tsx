import i18next from "i18next"
import { renderToStaticMarkup } from "react-dom/server"
import { I18nextProvider, initReactI18next } from "react-i18next"
import { beforeAll, describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }))

const { i18n: texts } = await import("./i18n")
const { ConnectionForm } = await import("./_ConnectionForm")
const { ConnectionStatusBox } = await import("./_ConnectionStatus")
const { SetupGuide } = await import("./SetupGuide")
const { ConnectionSettings } = await import("./ConnectionSettings")
const { FoundationOverview } = await import("./_FoundationOverview")
const { DEFAULTS } = await import("./connectionLogic")

const inst = i18next.createInstance()
beforeAll(async () => {
  await inst.use(initReactI18next).init({
    lng: "de", fallbackLng: "de", ns: ["voip"], defaultNS: "voip",
    resources: { de: { voip: texts.de.voip }, en: { voip: texts.en.voip } }, interpolation: { escapeValue: false },
  })
})
const html = (el: React.ReactElement) => renderToStaticMarkup(<I18nextProvider i18n={inst}>{el}</I18nextProvider>)

describe("Formular", () => {
  it("alle Zugangsdaten-Felder", () => {
    const h = html(<ConnectionForm form={DEFAULTS} hasPassword={false} disabled={false} onChange={() => {}} />)
    for (const f of ["pbx", "display_name", "registrar", "registrar_port", "username", "password", "own_number",
      "local_sip_port", "rtp_port_min", "rtp_port_max", "register_interval"]) {
      expect(h).toContain(`data-voip-field="${f}"`)
    }
    expect(h).toContain('value="fritz.box"')
    expect(h).toContain("FRITZ!Box")
    expect(h).toContain("Andere SIP-Anlage")
  })
  it("Kennwort: Typ password, nie vorausgefüllt, Hinweis wenn gespeichert", () => {
    const h = html(<ConnectionForm form={{ ...DEFAULTS, password: "" }} hasPassword={true} disabled={false} onChange={() => {}} />)
    expect(h).toMatch(/type="password"[^>]*value=""/)
    expect(h).toMatch(/autocomplete="new-password"/i)
    expect(h).toContain("gespeichert – leer lassen")
  })
})

describe("Status", () => {
  it.each(["registered", "auth_failed", "unreachable", "rejected", "blocked", "port_in_use", "not_found",
    "disconnected", "connecting", "not_configured", "secret_invalid"] as const)("%s hat Titel und Hinweis", (s) => {
    const h = html(<ConnectionStatusBox status={s} />)
    expect(h).toContain(`data-voip-status="${s}"`)
    expect(h).not.toContain(`conn.status.${s}`)          // Schlüssel aufgelöst, kein Rohtext
  })
  it("falsches Kennwort: verständlich, mit Weg in der FRITZ!Box", () => {
    const h = html(<ConnectionStatusBox status="auth_failed" />)
    expect(h).toContain("Benutzername oder Kennwort falsch")
    expect(h).toContain("Telefoniegeräte")
  })
})

describe("Anleitung und Router-Hinweis", () => {
  it("FRITZ!Box-Schritte", () => {
    const h = html(<SetupGuide form={DEFAULTS} />)
    expect(h).toContain('data-voip-guide="1"')
    expect(h).toContain("Telefoniegeräte")
    expect(h).toContain("LAN/WLAN (IP-Telefon)")
    expect((h.match(/<li>/g) ?? []).length).toBeGreaterThanOrEqual(7 + 5)
  })
  it("Router-Hinweis nennt die eingetragenen Ports", () => {
    const h = html(<SetupGuide form={{ ...DEFAULTS, local_sip_port: 5099, rtp_port_min: 8000, rtp_port_max: 8020 }} />)
    expect(h).toContain('data-voip-router="1"')
    expect(h).toContain("UDP 5099")
    expect(h).toContain("8000–8020")
    expect(h).toContain("SIP-ALG")
    expect(h).toContain("Niemals SIP-Ports der FRITZ!Box ins Internet")
    expect(h).not.toContain("{{")
  })
})

describe("Seite", () => {
  it("Verbinden-Knopf, Speichern-Knopf, Anleitung", () => {
    const h = html(<ConnectionSettings />)
    expect(h).toContain('data-voip-connect="1"')
    expect(h).toContain('data-voip-save="1"')
    expect(h).toContain(">Verbinden<")
    expect(h).toContain('data-voip-guide="1"')
    expect(h).toContain("Telefon-Agent und selbst anrufen folgen")
  })
  it("Übersicht: ehrlicher Stand und Weg zur Einrichtung", () => {
    const h = html(<FoundationOverview status="registered" onSetup={() => {}} />)
    expect(h).toContain(">Verbindung</span>")
    expect((h.match(/>Verbunden</g) ?? []).length).toBe(2)          // Karte + Statusbox
    expect(h).toContain('data-voip-goto-settings="1"')
    expect(h).toContain("Abnehmen mit Ansage")
  })
})

describe("Texte vollständig", () => {
  const keys = (o: unknown, p = ""): string[] => typeof o === "object" && o !== null && !Array.isArray(o)
    ? Object.entries(o).flatMap(([k, v]) => keys(v, p ? `${p}.${k}` : k)) : [p]
  it("DE und EN haben dieselben Schlüssel", () => {
    expect(keys(texts.en.voip).sort()).toEqual(keys(texts.de.voip).sort())
  })
  it("Anleitung DE/EN gleich viele Schritte", () => {
    expect(texts.en.voip.conn.guide.steps.length).toBe(texts.de.voip.conn.guide.steps.length)
    expect(texts.en.voip.conn.router.points.length).toBe(texts.de.voip.conn.router.points.length)
  })
})
