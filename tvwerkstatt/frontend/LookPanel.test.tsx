import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: Record<string, unknown>) => o ? `${k}(${Object.values(o).join(",")})` : k,
}) }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "" }) } }))
import type { TvwApp } from "./api"
import { LookPanel } from "./LookPanel"
import { DEFAULT_LOOK } from "./testLook"
import { TvPreview } from "./TvPreview"

const APPS: TvwApp[] = [{ package: "com.netflix.ninja", label: "Netflix", version: "1", has_banner: 1, color: "" },
  { package: "com.plexapp.android", label: "Plex", version: "1", has_banner: 1, color: "" }]
const f = () => {}
const panel = (look = DEFAULT_LOOK, apps = APPS) => renderToStaticMarkup(
  <LookPanel look={look} apps={apps} walls={[]} mood="night" onMood={f} onChange={f} onUpload={f} onDeleteWall={f}
    wallPath={(id) => id} />)

describe("TV-Werkstatt: Aussehen und Vorschau", () => {
  it("Kasten Aussehen wie die Demo: Tageszeiten, eigenes Bild, Abdunkeln, Kacheln 4–7, Apps", () => {
    const out = panel()
    for (const k of ["mood.morning", "mood.evening", "mood.night", "desk.own_image(mood.night)", "desk.dim",
      "desk.columns", "desk.dock_title", "Netflix", "Plex"]) expect(out, k).toContain(k)
    for (const n of [4, 5, 6, 7]) expect(out).toContain(`>${n}</button>`)
    expect(out).toMatch(/aria-pressed="true"[^>]*>6</)
  })

  it("Apps in der Leiste: Ziehen, hoch/runter, Schalter an", () => {
    const out = panel({ ...DEFAULT_LOOK, dock: ["com.plexapp.android"] })
    expect(out).toContain('draggable="true"')
    expect(out).toContain("desk.up")
    expect(out).toMatch(/role="switch" aria-checked="true"/)
    expect(out).toContain("desk.other_apps")
  })

  it("ohne Apps: Hinweis, sie erst zu lesen", () => {
    expect(panel(DEFAULT_LOOK, [])).toContain("desk.read_first")
  })

  it("Vorschau: Uhr, Pillen, Leiste mit Fokus auf der ersten App, Titel = erste App", () => {
    const out = renderToStaticMarkup(<TvPreview apps={APPS} look={{ ...DEFAULT_LOOK, dock: ["com.plexapp.android"] }}
      mood="evening" wallpaper={null} imagePath={(p) => p} now={new Date(2026, 10, 13, 20, 14)} />)
    expect(out).toContain("20:14")
    expect(out).toContain("desk.pill_inputs")
    expect(out).toContain("desk.greet_evening")
    expect(out.indexOf(">Plex<")).toBeLessThan(out.indexOf(">Netflix<"))
    expect(out).toMatch(/outline-white[^>]*title="Plex"/)
  })
})
