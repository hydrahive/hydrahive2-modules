import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
import { studioI18n } from "./i18n"
import { InspectorPanel } from "./InspectorPanel"
import { StudioPage } from "./StudioPage"
import { TimelinePanel } from "./TimelinePanel"
import { SHORTCUTS } from "./shortcuts"

const noop = () => {}
const attr = (out: string, name: string) => [...out.matchAll(new RegExp(`${name}="([^"]+)"`, "g"))].map((m) => m[1])

function strings(obj: unknown, path = ""): [string, string][] {
  if (typeof obj === "string") return [[path, obj]]
  if (obj && typeof obj === "object") return Object.entries(obj).flatMap(([k, v]) => strings(v, path ? `${path}.${k}` : k))
  return []
}

describe("Studio-Attrappe (Etappe 0)", () => {
  it("Gerüst: Bibliothek, Vorschau, Eigenschaften, Zeitleiste – sechs Arbeitsbereiche, Start in „Schneiden“", () => {
    const out = renderToStaticMarkup(<StudioPage />)
    expect(attr(out, "data-studio-panel")).toEqual(["library", "preview", "inspector", "timeline"])
    expect(attr(out, "data-studio-workspace")).toEqual(["plan", "generate", "edit", "audio", "subtitles", "deliver"])
    expect(out).toContain('data-studio-ws="edit"')
    expect(attr(out, "data-studio-splitter")).toEqual(["x", "x", "y"])
    expect(out).toContain("mockup_banner")
  })

  it("Hauptmenü von HydraHive bleibt oben (Till, 15.10.): Kern-Kopfleiste vor der Studio-Leiste", () => {
    const out = renderToStaticMarkup(<StudioPage />)
    const top = out.indexOf('href="/buddy"') >= 0 ? out.indexOf('href="/buddy"') : out.search(/Buddy|Projekte/)
    expect(top).toBeGreaterThanOrEqual(0)
    expect(top).toBeLessThan(out.indexOf("data-studio-root"))
  })

  it("Zeitleiste: Übersicht, Spuren aller Arten, Platzhalter-Clip erkennbar", () => {
    const out = renderToStaticMarkup(<TimelinePanel time={8} view={{ start: 0, span: 40 }} snap selected={null} focus="all"
      onView={noop} onSeek={noop} onSelect={noop} onSnap={noop} />)
    expect(out).toContain("data-studio-overview")
    expect(attr(out, "data-studio-track")).toEqual(["text", "video", "voice", "music", "subtitle"])
    expect(out).toMatch(/data-studio-clip="c4" data-placeholder="1"/)
    expect(out).toContain("data-studio-playhead")
  })

  it("Platzhalter gewählt → rechts erscheint „Erzeugen“ mit dem Shot", () => {
    const out = renderToStaticMarkup(<InspectorPanel workspace="edit" clipId="c4" mediaId={null} />).replace(/&quot;/g, '"')
    expect(out).toContain("data-studio-generate")
    expect(out).toContain('fill_placeholder:{"name":"Shot 3 – Sturm zieht auf"}')
    const normal = renderToStaticMarkup(<InspectorPanel workspace="edit" clipId="c2" mediaId={null} />)
    expect(normal).not.toContain("data-studio-generate")
  })

  it("Texte: de/en gleich, jedes Kürzel hat einen Namen, keine Terminal-Hinweise", () => {
    const de = strings(studioI18n.de.studio).map(([k]) => k).sort()
    expect(strings(studioI18n.en.studio).map(([k]) => k).sort()).toEqual(de)
    for (const s of SHORTCUTS) expect(de).toContain(`action.${s.action}`)
    const bad = [...strings(studioI18n.de), ...strings(studioI18n.en)].filter(([, v]) => /terminal|shell|sudo|install\.conf|HH_[A-Z]/i.test(v))
    expect(bad).toEqual([])
  })
})
