import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn() } }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (f: (s: unknown) => unknown) => f({ token: "t", username: "till", role: "user" }) }))
import { StationView } from "./StationPanel"
import { listenerUrl, stationErrorKey, type Station } from "./stationLogic"
import { radiostreamI18n } from "./i18n"

const BASE: Station = {
  installed: true, running: true, listeners: 4, can_control: true,
  now: { artist: "Queen", title: "One Vision" },
  recent: [{ track_id: "t_1", played_at: "2026-10-29T21:00:00Z", artist: "ABBA", title: "SOS" }],
  settings: { name: "Molke FM", subtitle: "rund um die Uhr", artist_gap_min: 60, title_gap_days: 3, listen_port: 8800,
    reach: "all", max_listeners: 50 },
}
const view = (s: Partial<Station>) => renderToStaticMarkup(
  <StationView s={{ ...BASE, ...s }} busy={false} msg={null} onStart={() => {}} onStop={() => {}} onSkip={() => {}} onSave={() => {}} host="hydra.local" />)

describe("Reiter Sender (Etappe 2)", () => {
  it("läuft: Jetzt läuft, Hörerzahl, zuletzt gespielt, Stoppen und Überspringen", () => {
    const html = view({})
    for (const s of ["station.on_air", "Queen", "One Vision", "station.listeners:{\"count\":4}", "ABBA", "SOS",
      "station.stop", "station.skip"]) expect(html).toContain(s)
    expect(html).not.toContain(">station.start<")
  })

  it("aus: Starten statt Stoppen, kein Überspringen", () => {
    const html = view({ running: false })
    expect(html).toContain("station.off")
    expect(html).toContain("station.start")
    expect(html).not.toContain("station.skip")
  })

  it("ohne Freigabe: sieht alles, aber keine Knöpfe und keine Einstellungen", () => {
    const html = view({ can_control: false })
    expect(html).toContain("One Vision")
    for (const k of ["station.stop", "station.skip", "station.start", "station.save"]) expect(html).not.toContain(k)
  })

  it("nicht eingerichtet: klarer Hinweis statt Starten", () => {
    const html = view({ installed: false, running: false })
    expect(html).toContain("station.not_installed")
    expect(html).not.toContain("station.start")
  })

  it("Einstellungen: Name, Untertitel, Sperren, Erreichbarkeit, Port, Höchstzahl, Speichern", () => {
    const html = view({})
    for (const k of ["station.name", "station.subtitle_label", "station.artist_gap", "station.title_gap", "station.reach",
      "station.reach_all", "station.reach_home", "station.reach_off", "station.port", "station.max_listeners", "station.save"])
      expect(html).toContain(k)
  })

  it("Hinweis Router nur bei „Alle“, Link zur Hörer-Seite nur wenn erreichbar", () => {
    expect(view({ settings: { ...BASE.settings, reach: "all" } })).toContain("station.router_hint")
    expect(view({ settings: { ...BASE.settings, reach: "home" } })).not.toContain("station.router_hint")
    expect(view({})).toContain('href="http://hydra.local:8800/"')
    expect(view({ settings: { ...BASE.settings, reach: "off" } })).not.toContain(":8800/")
    expect(view({ running: false })).not.toContain(":8800/")
  })

  it("keine Technik-Wörter in der Oberfläche (beide Sprachen)", () => {
    const flat = (o: unknown): string[] => typeof o === "string" ? [o] : Object.values(o as object).flatMap(flat)
    for (const lang of ["de", "en"] as const) {
      const st = (radiostreamI18n[lang].radiostream as unknown as { station: unknown }).station
      const text = flat(st).join(" ")
      expect(text).not.toMatch(/liquidsoap|icecast|nginx|systemd|sudo/i)
      expect(text.length).toBeGreaterThan(200)
    }
  })

  it("Link zur Hörer-Seite: Host ohne Port, IPv6 in Klammern", () => {
    expect(listenerUrl("hydra.local", 8800)).toBe("http://hydra.local:8800/")
    expect(listenerUrl("192.168.178.20:5173", 8801)).toBe("http://192.168.178.20:8801/")
    expect(listenerUrl("[fd00::1]:443", 8800)).toBe("http://[fd00::1]:8800/")
    expect(listenerUrl("fd00::1", 8800)).toBe("http://[fd00::1]:8800/")
  })

  it("Fehler des Senders bekommen eigene Texte, Freigabe fehlt auch", () => {
    for (const c of ["radiostream_service_missing", "radiostream_service_failed", "radiostream_not_running",
      "radiostream_port_in_use", "radiostream_nginx_failed", "radiostream_port_invalid", "radiostream_station_invalid"])
      expect(stationErrorKey(Object.assign(new Error("x"), { code: c }))).toBe(`err.${c}`)
    expect(stationErrorKey(Object.assign(new Error("x"), { code: "capability_denied" }))).toBe("err.radiostream_admin_only")
    expect(stationErrorKey("kaputt")).toBe("err.general")
  })
})
