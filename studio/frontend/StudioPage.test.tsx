import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import type { LibraryItem } from "./api"
import { studioI18n } from "./i18n"
import { InspectorPanel } from "./InspectorPanel"
import { LibraryPanel } from "./LibraryPanel"
import { MediaView } from "./MediaView"
import { StudioPage } from "./StudioPage"
import { TimelinePanel } from "./TimelinePanel"
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
  it("Gerüst mit Hauptmenü oben, vier Bereiche, sechs Arbeitsbereiche, Zeitleiste als Beispiel markiert", () => {
    const out = html(<StudioPage />)
    expect(attr(out, "data-studio-panel")).toEqual(["library", "preview", "inspector", "timeline"])
    expect(attr(out, "data-studio-workspace")).toEqual(["plan", "generate", "edit", "audio", "subtitles", "deliver"])
    expect(attr(out, "data-studio-splitter")).toEqual(["x", "x", "y"])
    const top = out.search(/href="\/buddy"|Buddy|Projekte/)
    expect(top).toBeGreaterThanOrEqual(0)
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

  it("Eigenschaften: Angaben zum Medium inkl. Beschreibung; Platzhalter zeigt „Erzeugen“ (noch gesperrt)", () => {
    const info = html(<InspectorPanel workspace="edit" clipId={null} item={ITEMS[1]} />)
    expect(info).toContain('data-studio-info="i2"')
    expect(info).toContain("Leuchtturm")
    expect(info).toContain("source.atelier")
    const gen = html(<InspectorPanel workspace="edit" clipId="c4" item={null} />)
    expect(gen).toContain("data-studio-generate")
    expect(gen).toContain('fill_placeholder:{"name":"Shot 3 – Sturm zieht auf"}')
    expect(gen).toContain("generate_soon")
  })

  it("Zeitleiste (noch Beispiel): Übersicht, alle Spurarten, Platzhalter", () => {
    const out = html(<TimelinePanel time={8} view={{ start: 0, span: 40 }} snap selected={null} focus="all"
      onView={noop} onSeek={noop} onSelect={noop} onSnap={noop} />)
    expect(out).toContain("data-studio-overview")
    expect(attr(out, "data-studio-track")).toEqual(["text", "video", "voice", "music", "subtitle"])
    expect(out).toMatch(/data-studio-clip="c4" data-placeholder="1"/)
    expect(out).toContain("data-studio-demo-badge")              // als Beispiel markiert, in der eigenen Leiste
  })

  it("Texte: de/en gleich, jedes Kürzel hat einen Namen, keine Terminal-Hinweise", () => {
    const de = strings(studioI18n.de.studio).map(([k]) => k).sort()
    expect(strings(studioI18n.en.studio).map(([k]) => k).sort()).toEqual(de)
    for (const s of SHORTCUTS) expect(de).toContain(`action.${s.action}`)
    const bad = [...strings(studioI18n.de), ...strings(studioI18n.en)].filter(([, v]) => /terminal|shell|sudo|install\.conf|HH_[A-Z]/i.test(v))
    expect(bad).toEqual([])
  })
})
