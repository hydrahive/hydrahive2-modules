import { renderToStaticMarkup } from "react-dom/server"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k), i18n: { language: "de", resolvedLanguage: "de", changeLanguage: () => Promise.resolve() } }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import type { LibraryItem } from "./api"
import { studioI18n } from "./i18n"
import { LibraryPanel } from "./LibraryPanel"
import { MediaInfo } from "./MediaInfo"
import { MediaView } from "./MediaView"
import { StudioPage } from "./StudioPage"
import { SHORTCUTS } from "./shortcuts"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const attr = (out: string, name: string) => [...out.matchAll(new RegExp(`${name}="([^"]+)"`, "g"))].map((m) => m[1])

function strings(obj: unknown, path = ""): [string, string][] {
  if (typeof obj === "string") return [[path, obj]]
  if (obj && typeof obj === "object") return Object.entries(obj).flatMap(([k, v]) => strings(v, path ? `${path}.${k}` : k))
  return []
}

const item = (p: Partial<LibraryItem>): LibraryItem => ({
  id: "i1", kind: "video", origin: "ai", source: "atelier", name: "Mira am Steg", rel: "atelier/videos/v.mp4",
  abs: "/data/w/atelier/videos/v.mp4", size: 2048, created_at: "2026-10-15T08:00:00Z", ...p,
})
const ITEMS = [
  item({}),
  item({ id: "i2", kind: "image", name: "Titel", abs: "/data/w/atelier/images/t.png", prompt: "Leuchtturm" }),
  item({ id: "i3", kind: "video", name: "Drohne", origin: "upload", source: "videoeditor" }),
  item({ id: "i4", kind: "element", name: "Mira", thumb_abs: "/data/w/atelier/characters/c/a.png" }),
]

describe("Studio Etappe 1", () => {
  it("Gerüst mit Hauptmenü oben, vier Bereiche, sechs Arbeitsbereiche", () => {
    const out = html(<MemoryRouter initialEntries={["/studio"]}><StudioPage /></MemoryRouter>)
    expect(attr(out, "data-studio-panel")).toEqual(["sidebar", "preview", "inspector", "storyboard"])   // Start in „Planen“ (Etappe B)
    expect(attr(out, "data-studio-workspace")).toEqual(["plan", "generate", "edit", "audio", "subtitles", "deliver"])
    expect(attr(out, "data-studio-splitter")).toEqual(["x", "x", "y"])
    // Hauptmenü = Bereichs-Leiste des Kerns (#618): Start-Knopf + „Alle Apps“ stehen über dem Studio.
    const top = out.search(/aria-label="Start"/)
    expect(top).toBeGreaterThanOrEqual(0)
    expect(out.search(/aria-label="Alle Apps"/)).toBeLessThan(out.indexOf("data-studio-root"))
    expect(top).toBeLessThan(out.indexOf("data-studio-root"))
  })

  it("Bibliothek: echte Einträge in Ordnern KI-erzeugt / Hochgeladen, Vorschaubild über /api/files", () => {
    const out = html(<LibraryPanel items={ITEMS} loading={false} error={null} truncated={false} selected="i1" onSelect={noop} />)
    expect(attr(out, "data-library-item")).toEqual(["i1", "i2", "i4", "i3"])
    expect(out.indexOf("origin.ai")).toBeLessThan(out.indexOf("origin.upload"))
    expect(out).toContain("/api/files?path=%2Fdata%2Fw%2Fatelier%2Fimages%2Ft.png")
    expect(out).toContain('data-library-count="4"')
  })

  it("Bibliothek: leer, Fehler, gekürzt", () => {
    expect(html(<LibraryPanel items={[]} loading={false} error={null} truncated={false} selected={null} onSelect={noop} />)).toContain("library_none")
    expect(html(<LibraryPanel items={[]} loading={false} error="kaputt" truncated={false} selected={null} onSelect={noop} />)).toContain("data-library-error")
    expect(html(<LibraryPanel items={ITEMS} loading={false} error={null} truncated selected={null} onSelect={noop} />)).toContain("library_truncated")
  })

  it("Vorschau zeigt das echte Medium je Art", () => {
    expect(html(<MediaView item={ITEMS[0]} bind={noop} />)).toMatch(/<video[^>]*src="\/api\/files\?path=%2Fdata%2Fw%2Fatelier%2Fvideos%2Fv\.mp4/)
    expect(html(<MediaView item={ITEMS[1]} bind={noop} />)).toContain('data-studio-preview="image"')
    expect(html(<MediaView item={item({ kind: "music" })} bind={noop} />)).toContain('data-studio-preview="audio"')
    expect(html(<MediaView item={ITEMS[3]} bind={noop} />)).toContain('data-studio-preview="element"')
    expect(html(<MediaView item={null} bind={noop} />)).toContain("preview_empty")
  })

  it("Eigenschaften: Angaben zum Medium inkl. Beschreibung; ohne Medium ein Hinweis", () => {
    const info = html(<MediaInfo item={ITEMS[1]} />)
    expect(info).toContain('data-studio-info="i2"')
    expect(info).toContain("Leuchtturm")
    expect(info).toContain("source.atelier")
    expect(html(<MediaInfo item={null} />)).toContain("pick_medium")
  })

  it("Texte: de/en gleich, jedes Kürzel hat einen Namen, keine Terminal-Hinweise", () => {
    const de = strings(studioI18n.de.studio).map(([k]) => k).sort()
    expect(strings(studioI18n.en.studio).map(([k]) => k).sort()).toEqual(de)
    for (const s of SHORTCUTS) expect(de).toContain(`action.${s.action}`)
    const bad = [...strings(studioI18n.de), ...strings(studioI18n.en)].filter(([, v]) => /terminal|shell|sudo|install\.conf|HH_[A-Z]/i.test(v))
    expect(bad).toEqual([])
  })

  it("Jeder im Code benutzte Text-Schlüssel existiert in de und en (auch zusammengesetzte wie `gen.${k}`)", () => {
    const files = import.meta.glob(["./*.ts", "./*.tsx", "!./*.test.ts", "!./*.test.tsx", "!./i18n*.ts"], { query: "?raw", import: "default", eager: true })
    const code = Object.values(files).join("\n")
    const has = (obj: unknown, path: string) => path.split(".").reduce<unknown>((o, k) => (o && typeof o === "object" ? (o as Record<string, unknown>)[k] : undefined), obj) !== undefined
    const plain = [...code.matchAll(/\bt\("([a-z_]+(?:\.[a-z_]+)*)"/g)].map((m) => m[1])
    const prefixes = [...code.matchAll(/\bt\(`([a-z_]+)\.\$\{/g)].map((m) => m[1])
    expect(plain.length).toBeGreaterThan(50)
    expect(prefixes.length).toBeGreaterThan(10)
    for (const lang of ["de", "en"] as const) {
      const s = studioI18n[lang].studio
      const plural = (k: string) => has(s, `${k}_one`) && has(s, `${k}_other`)
      expect(plain.filter((k) => !has(s, k) && !plural(k)), lang).toEqual([])
      expect(prefixes.filter((k) => { const v = (s as Record<string, unknown>)[k]; return !v || typeof v !== "object" }), lang).toEqual([])
    }
  })
})
