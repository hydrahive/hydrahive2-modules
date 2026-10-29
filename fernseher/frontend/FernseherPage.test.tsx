import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn() } }))
let role = "admin"
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: (f: (s: unknown) => unknown) => f({ token: "t", username: "till", role }) }))
import { FernseherPage } from "./FernseherPage"
import { NowPlaying } from "./NowPlaying"
import { Remote } from "./Remote"
import { Setup } from "./Setup"
import { fernseherI18n } from "./i18n"
import { ERROR_CODES } from "./logic"

const ON = { power: "on" as const, channel: { number: 6, name: "SAT.1" }, program: "Richter Alexander Hold", volume: 14, muted: false, model: "KD-60XF8305" }

function keys(o: Record<string, unknown>, p = ""): string[] {
  return Object.entries(o).flatMap(([k, v]) => (v && typeof v === "object" ? keys(v as Record<string, unknown>, `${p}${k}.`) : [`${p}${k}`]))
}

describe("Seite Fernseher", () => {
  it("Admin sieht das Einrichten", () => {
    role = "admin"
    expect(renderToStaticMarkup(<FernseherPage />)).toContain("data-tv-setup")
  })

  it("Nutzer ohne Adminrecht sieht kein Einrichten", () => {
    role = "user"
    expect(renderToStaticMarkup(<FernseherPage />)).not.toContain("data-tv-setup")
    role = "admin"
  })

  it("Läuft gerade: Sender, Platz, Sendung, Lautstärke", () => {
    const html = renderToStaticMarkup(<NowPlaying status={ON} />)
    for (const s of ["SAT.1", ">6<", "Richter Alexander Hold", 'now.volume:{&quot;volume&quot;:14}']) expect(html).toContain(s)
    expect(html).not.toContain("now.muted")
  })

  it("Läuft gerade: aus, stumm, App", () => {
    expect(renderToStaticMarkup(<NowPlaying status={{ ...ON, power: "standby" }} />)).toContain("now.off")
    expect(renderToStaticMarkup(<NowPlaying status={{ ...ON, muted: true }} />)).toContain("now.muted")
    expect(renderToStaticMarkup(<NowPlaying status={{ ...ON, channel: null, program: "" }} />)).toContain("now.app")
  })

  it("Fernbedienung: an → Ausschalten und Lautstärke aktiv; aus → Einschalten, Lautstärke gesperrt", () => {
    const on = renderToStaticMarkup(<Remote status={ON} onChange={() => {}} />)
    expect(on).toContain("remote.off")
    expect(on).toContain("remote.louder")
    expect(on).toContain("remote.mute")
    const off = renderToStaticMarkup(<Remote status={{ ...ON, power: "standby" }} onChange={() => {}} />)
    expect(off).toContain("remote.on")
    expect((off.match(/disabled=""/g) ?? []).length).toBe(3)
  })

  it("Einrichten: Schlüsselfeld ist ein Passwortfeld ohne Vorbelegung, mit Hinweis, wo man ihn am TV setzt", () => {
    const html = renderToStaticMarkup(<Setup onSaved={() => {}} />)
    expect(html).toContain('type="password"')
    expect(html).toContain('autoComplete="new-password"')
    expect(html).toContain("setup.psk_hint")
    expect(html).toMatch(/type="password"[^>]*value=""/)
  })

  it("Deutsch und Englisch haben dieselben Texte, jeder Fehlercode hat einen Text, keine Doppelpunkte in Schlüsseln", () => {
    const de = keys(fernseherI18n.de).sort()
    const en = keys(fernseherI18n.en).sort()
    expect(en).toEqual(de)
    for (const code of ERROR_CODES) expect(de).toContain(`fernseher.err.${code}`)
    expect(de).toContain("fernseher.err.general")
    expect(de.every((k) => !k.includes(":"))).toBe(true)
  })

  it("Texte ohne Fachwörter oder Hinweise auf Terminal/Dateien", () => {
    // Nur die sichtbaren Texte prüfen, nicht die Schlüsselnamen (psk_hint o. ä. sieht niemand)
    const values = (o: Record<string, unknown>): string[] =>
      Object.values(o).flatMap((v) => (v && typeof v === "object" ? values(v as Record<string, unknown>) : [String(v)]))
    const all = values(fernseherI18n).join(" ").toLowerCase()
    for (const w of ["terminal", "konsole", "shell", "json", " api", "datei", "psk", "http", "curl", "ssh", "jsonrpc"])
      expect(all).not.toContain(w)
  })
})
