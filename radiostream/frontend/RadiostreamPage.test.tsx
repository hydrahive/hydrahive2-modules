import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn() } }))
const role = { value: "admin" }
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (f: (s: unknown) => unknown) => f({ token: "t", username: "till", role: role.value }) }))
import { RadiostreamPage } from "./RadiostreamPage"
import { StatsBar } from "./StatsBar"
import { TrackRow } from "./TrackRow"
import { SettingsPanel } from "./SettingsPanel"

const TRACK = { track_id: "t_1", artist: "Queen", album_artist: "", title: "One Vision", album: "A Kind of Magic", genre: "Rock",
  year: 1986, track_no: 1, duration_s: 310.2, bitrate: 320000, sample_rate: 44100, format: "mp3", state: "ok" }

describe("Seite Radiostream (Etappe 1: Bibliothek)", () => {
  it("Kopf, Reiter Bibliothek, Suche und Filter", () => {
    const html = renderToStaticMarkup(<RadiostreamPage />)
    for (const k of ["title", "tab.library", "search_placeholder", "filter.all_genres", "filter.all_decades", "filter.all_formats"]) expect(html).toContain(k)
  })

  it("Admin sieht Einstellungen, Nutzer nicht", () => {
    role.value = "admin"
    expect(renderToStaticMarkup(<RadiostreamPage />)).toContain("tab.settings")
    role.value = "user"
    expect(renderToStaticMarkup(<RadiostreamPage />)).not.toContain("tab.settings")
    role.value = "admin"
  })

  it("Zahlen oben in Worten", () => {
    const html = renderToStaticMarkup(<StatsBar stats={{ tracks: 175402, duration_s: 3600 * 24 * 500, artists: 2515, missing: 0, errors: 3,
      formats: { mp3: 117922, flac: 57444 }, genres: [], decades: [] }} />)
    expect(html).toContain("175.402")
    expect(html).toContain("2.515")
    expect(html).toContain("stats.days")
  })

  it("Zeile: Künstler, Titel, Album, Jahr, Länge, Format, Vorhören", () => {
    const html = renderToStaticMarkup(<table><tbody><TrackRow t={TRACK} playing={false} onPlay={() => {}} /></tbody></table>)
    for (const s of ["Queen", "One Vision", "A Kind of Magic", "1986", "5:10", "MP3"]) expect(html).toContain(s)
    expect(html).toContain("aria-label=\"play\"")
  })

  it("Einstellungen: Adresse, Zugang aus dem Safe, prüfen, speichern, einlesen – ohne Passwortfeld", () => {
    const html = renderToStaticMarkup(<SettingsPanel onSaved={() => {}} />)
    for (const k of ["settings.url", "settings.credential", "settings.test", "settings.save", "settings.scan_now"]) expect(html).toContain(k)
    expect(html).not.toMatch(/type="password"/)
  })
})
