import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
const post = vi.fn((..._a: unknown[]) => new Promise(() => {}))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: (...a: unknown[]) => post(...a) } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import { DeliverPanel } from "./DeliverPanel"
import { DeliverPreset } from "./DeliverPreset"
import i18next from "i18next"
import { ASPECTS, QUALITIES, aspectKey, downloadName, outputSize, presetLabel } from "./deliverLogic"
import { studioI18n } from "./i18n"
import { renderApi, type RenderItem } from "./renderApi"
import type { TimelineClip } from "./timelineApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const clip: TimelineClip = { id: "c", kind: "video", start: 0, in: 0, out: 4, media_rel: "x", scene_id: "", shot_id: "", label: "l" }
const R = (p: Partial<RenderItem>): RenderItem => ({ rel: "studio/renders/a.mp4", abs: "/w/studio/renders/a.mp4", name: "a.mp4", duration: 12.5,
  width: 720, height: 1280, created_at: "2026-10-19T08:12:00Z", missing: 0, clips: 3, ...p })
const base = { clips: [clip], renders: [], job: null, busy: false, onRender: noop, onCut: noop }

describe("7b – Vorlagen: Größen wie auf dem Server", () => {
  it("kürzere Seite = Qualität, längere aus dem Format, gerade gerundet; „wie im Drehbuch“ nimmt das Drehbuch", () => {
    expect(outputSize("16:9", "preview", "9:16")).toEqual([854, 480])
    expect(outputSize("16:9", "standard", "9:16")).toEqual([1280, 720])
    expect(outputSize("16:9", "high", "9:16")).toEqual([1920, 1080])
    expect(outputSize("9:16", "preview", "16:9")).toEqual([480, 854])
    expect(outputSize("9:16", "high", "16:9")).toEqual([1080, 1920])
    expect(outputSize("1:1", "standard", "16:9")).toEqual([720, 720])
    expect(outputSize("screenplay", "standard", "4:3")).toEqual([960, 720])
    expect(outputSize("screenplay", "high", "21:9")).toEqual([2520, 1080])
    expect(outputSize("screenplay", "preview", "kaputt")).toEqual([854, 480])
    expect(ASPECTS).toEqual(["screenplay", "16:9", "9:16", "1:1"])
    expect(QUALITIES).toEqual(["preview", "standard", "high"])
  })

  it("dieselben Werte wie backend/render_preset.py (Tabelle im Python-Code)", () => {
    const src = Object.values(import.meta.glob("../backend/render_preset.py", { query: "?raw", import: "default", eager: true })).join("")
    expect(src).toMatch(/"preview":\s*\(480,\s*28\)/)
    expect(src).toMatch(/"standard":\s*\(720,\s*23\)/)
    expect(src).toMatch(/"high":\s*\(1080,\s*20\)/)
  })
})

describe("7b – Vorlagen: Reiter „Ausgabe“", () => {
  it("zwei Auswahlfelder mit allen Werten, gewählte Werte markiert, Ergebnisgröße darunter", () => {
    const out = html(<DeliverPanel {...base} aspect="16:9" preset={{ aspect: "9:16", quality: "high" }} onPreset={noop} />)
    for (const a of ASPECTS) expect(out).toContain(`value="${a}"`)
    for (const q of QUALITIES) expect(out).toContain(`value="${q}"`)
    expect(out).toMatch(/<select[^>]*data-deliver-aspect[^>]*>/)
    expect(out).toMatch(/<select[^>]*data-deliver-quality[^>]*>/)
    expect(out).toMatch(/<option value="9:16" selected="">/)
    expect(out).toMatch(/<option value="high" selected="">/)
    expect(out).toContain('deliver_result:{"width":1080,"height":1920}')
    expect(out).toContain('deliver_aspect.screenplay:{"aspect":"16:9"}')            // „wie im Drehbuch (16:9)“
  })

  it("ohne Vorlage: „wie im Drehbuch“ und „Standard“; die Übersicht nennt keine Größe mehr", () => {
    const out = html(<DeliverPanel {...base} aspect="9:16" />)
    expect(out).toMatch(/<option value="screenplay" selected="">/)
    expect(out).toMatch(/<option value="standard" selected="">/)
    expect(out).toContain('deliver_result:{"width":720,"height":1280}')
    expect(out).toContain('deliver_summary:{"length":"0:04","clips":1}')
  })

  it("fertiger Film nennt Format und Qualität; ältere Filme nur die Größe", () => {
    const out = html(<DeliverPanel {...base} aspect="16:9" renders={[R({ aspect: "9:16", quality: "standard" }), R({ rel: "b", abs: "/b", name: "b.mp4", width: 1280, height: 720 })]} />)
    expect(out).toContain('deliver_film_preset:{"aspect":"9:16","quality":"deliver_quality.standard"}')
    expect((out.match(/deliver_film_preset/g) || []).length).toBe(1)
  })

  it("Name beim Herunterladen enthält Format und Größe", () => {
    expect(downloadName(R({ aspect: "9:16", quality: "standard" }))).toBe("film-202610190812-9x16-720p.mp4")
    expect(downloadName(R({ aspect: "16:9", width: 1920, height: 1080 }))).toBe("film-202610190812-16x9-1080p.mp4")
    expect(downloadName(R({}))).toBe("film-202610190812-720x1280.mp4")                       // alter Film ohne Vorlage
    expect(downloadName(R({ created_at: null, width: null, height: null }))).toBe("film-a.mp4")
    const out = html(<DeliverPanel {...base} aspect="16:9" renders={[R({ aspect: "1:1", width: 480, height: 480 })]} />)
    expect(out).toContain('download="film-202610190812-1x1-480p.mp4"')
  })

  it("presetLabel: Format · Qualität (für Liste und Meldung)", () => {
    const t = (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k)
    expect(presetLabel(t, { aspect: "1:1", quality: "preview" })).toBe('deliver_film_preset:{"aspect":"1:1","quality":"deliver_quality.preview"}')
    expect(presetLabel(t, {})).toBe("")
    expect(presetLabel(t, { aspect: "9:16" })).toBe("")
    expect(presetLabel(t, { quality: "high" })).toBe("")
  })
})

describe("7b – Vorlage geht an den Server", () => {
  it("renderApi.start schickt aspect, quality und subtitles", () => {
    post.mockClear()
    void renderApi.start("p1", { aspect: "9:16", quality: "high", subtitles: true })
    expect(post).toHaveBeenCalledWith("/modules/studio/projects/p1/render", { aspect: "9:16", quality: "high", subtitles: true })
    void renderApi.start("p1", { aspect: "screenplay", quality: "standard", subtitles: false })
    expect(post).toHaveBeenLastCalledWith("/modules/studio/projects/p1/render", { aspect: "screenplay", quality: "standard" })
  })
})

describe("7b – Texte", () => {
  it("de/en: alle Formate, Qualitäten und der Fehler studio_render_bad_preset", () => {
    for (const lang of ["de", "en"] as const) {
      const s = studioI18n[lang].studio as unknown as Record<string, unknown> & { deliver_aspect: Record<string, string>; deliver_quality: Record<string, string>; deliver_err: Record<string, string> }
      for (const a of ASPECTS) expect(s.deliver_aspect[aspectKey(a).split(".")[1]], `${lang} ${a}`).toBeTruthy()
      for (const q of QUALITIES) expect(s.deliver_quality[q], `${lang} ${q}`).toBeTruthy()
      expect(s.deliver_err.studio_render_bad_preset).toBeTruthy()
      for (const k of ["deliver_result", "deliver_film_preset", "deliver_aspect_label", "deliver_quality_label"]) expect(s[k], `${lang} ${k}`).toBeTruthy()
      expect(s.deliver_aspect.screenplay).toContain("{{aspect}}")
    }
  })
})

type El = { type: unknown; props: Record<string, unknown> & { children?: unknown } }
const selects = (node: unknown, out: El[] = []): El[] => {
  if (Array.isArray(node)) node.forEach((n) => selects(n, out))
  else if (node && typeof node === "object" && "props" in node) {
    const el = node as El
    if (el.type === "select") out.push(el)
    selects(el.props.children, out)
  }
  return out
}

describe("7b – Vorlagen: Auswahl bedienen", () => {
  it("Format ändern behält die Qualität und umgekehrt", () => {
    const onChange = vi.fn()
    const tree = DeliverPreset({ preset: { aspect: "screenplay", quality: "high" }, screenplay: "16:9", onChange })
    const [aspect, quality] = selects(tree)
    expect(aspect.props["data-deliver-aspect"]).toBe(true)
    ;(aspect.props.onChange as (e: unknown) => void)({ target: { value: "9:16" } })
    expect(onChange).toHaveBeenLastCalledWith({ aspect: "9:16", quality: "high" })
    ;(quality.props.onChange as (e: unknown) => void)({ target: { value: "preview" } })
    expect(onChange).toHaveBeenLastCalledWith({ aspect: "screenplay", quality: "preview" })
  })

  it("während ein Film entsteht, sind beide Felder gesperrt", () => {
    const out = html(<DeliverPanel {...base} aspect="16:9" job={{ id: "j", kind: "render", target: "render:x", scene_id: "", status: "running", error: null,
      result: null, created_at: "x", finished_at: null, progress: { total: 100, done: 10, failed: 0, current: "" } }} />)
    expect(out).toMatch(/<select[^>]*disabled=""[^>]*data-deliver-aspect/)
    expect(out).toMatch(/<select[^>]*disabled=""[^>]*data-deliver-quality/)
    expect(html(<DeliverPanel {...base} aspect="16:9" />)).not.toMatch(/<select[^>]*disabled=""/)
  })
})

describe("7b – Texte mit echtem i18next (Doppelpunkt im Format)", () => {
  it("jedes Format zeigt seinen vollen Text, nicht nur die Zahl nach dem „:“", async () => {
    const inst = i18next.createInstance()
    await inst.init({ lng: "de", resources: studioI18n, ns: ["studio"], defaultNS: "studio", interpolation: { escapeValue: false } })
    const t = inst.getFixedT("de", "studio")
    expect(t(aspectKey("9:16"))).toBe("9:16 Hochformat (Handy, Reels, Shorts)")
    expect(t(aspectKey("16:9"))).toContain("16:9 Querformat")
    expect(t(aspectKey("1:1"))).toBe("1:1 Quadrat")
    expect(t("deliver_aspect.screenplay", { aspect: "4:3" })).toBe("Wie im Drehbuch (4:3)")
    expect(t("deliver_film_preset", { aspect: "9:16", quality: t("deliver_quality.preview") })).toBe("9:16 · Vorschau 480p")
  })
})
