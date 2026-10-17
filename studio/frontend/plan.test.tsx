import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o && !("defaultValue" in o) ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import type { LibraryItem } from "./api"
import { DeleteDialog } from "./DeleteDialog"
import { ElementForm } from "./ElementForm"
import { HeadForm } from "./HeadForm"
import { ImportDialog } from "./ImportDialog"
import type { ImportPreview, Plan } from "./planApi"
import { PlanOutline } from "./PlanOutline"
import { PlanPreview } from "./PlanPreview"
import { SceneForm } from "./SceneForm"
import { StoryboardPanel } from "./StoryboardPanel"

const noop = () => {}
const SB = { onSelect: noop, onAdd: noop, onMove: noop, onDecompose: noop }
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const attr = (out: string, name: string) => [...out.matchAll(new RegExp(`${name}="([^"]+)"`, "g"))].map((m) => m[1])
const shot = (id: string, image_rel: string | null) => ({ id, order: 0, shot: "closeup", prompt: `Prompt ${id}`, element_ids: [], duration: 5, status: "planned", image_rel, video_rel: null, variants: [] })

const PLAN: Plan = {
  base: "/data/w",
  screenplay: { title: "Sturm", logline: "Ein Hafen", description: "", aspect_ratio: "16:9", default_duration: 5,
    models: { video: "kling", image: "", voice: "", music: "", text: "" }, look: { style: "noir", palette: ["#111", "#222"] }, scene_order: ["s2", "s1"] },
  scenes: [
    { id: "s2", title: "Hafen", description: "Am Steg", location: "Steg", time_of_day: "dawn", element_ids: ["e1"],
      dialogues: [{ element_id: "e1", line: "Wo bist du?", emotion: "leise" }], camera: { shot: "closeup" },
      shots: [shot("h1", "atelier/images/a.png"), shot("h2", null)] },
    { id: "s1", title: "Sturm", description: "", location: "", time_of_day: "", element_ids: [], dialogues: [], camera: {}, shots: [] },
  ],
  elements: [
    { id: "e2", kind: "place", name: "Hafen", description: "", style_anchor: "", palette: [], references: [] },
    { id: "e1", kind: "character", name: "Mira", description: "Fischerin", style_anchor: "", palette: [], references: ["atelier/characters/c/a.png"] },
  ],
  presets: { shot: ["closeup", "wide"], lens: ["normal_50"], light: [], weather: [], time: [], mood: [] },
}
const EMPTY: Plan = { ...PLAN, screenplay: { ...PLAN.screenplay, title: "", scene_order: [] }, scenes: [], elements: [] }
const PREVIEW: ImportPreview = { available: true, scenes: 2, shots: 3, elements: 1, look: true, plan_exists: false }
const IMG = (id: string, abs: string): LibraryItem => ({ id, kind: "image", origin: "ai", source: "atelier", name: id, rel: abs.slice(8), abs, size: 1, created_at: "" })
const outline = (p: Partial<Parameters<typeof PlanOutline>[0]>) => html(
  <PlanOutline plan={PLAN} preview={null} selection={null} onSelect={noop} onMove={noop} onAddScene={noop} onAddElement={noop} onImport={noop} {...p} />)

describe("Studio Etappe 2a – Planen", () => {
  it("Gliederung: Kopf, Szenen in Reihenfolge, Bausteine nach Art, Auswahl markiert, Ränder gesperrt", () => {
    const out = outline({ selection: { kind: "scene", id: "s1" } })
    expect(out).toContain("data-plan-head")
    expect(attr(out, "data-plan-scene")).toEqual(["s2", "s1"])
    expect(attr(out, "data-plan-element")).toEqual(["e1", "e2"])            // Figuren vor Orten
    expect(out).toMatch(/data-plan-scene="s1"[^>]*aria-current="true"/)
    const btn = (key: string) => out.match(new RegExp(`<button[^>]*data-plan-move="${key}"[^>]*>`))?.[0] ?? ""
    expect(btn("s2:-1")).toContain(" disabled=\"\"")                       // erste Szene nicht weiter hoch
    expect(btn("s1:1")).toContain(" disabled=\"\"")                       // letzte Szene nicht weiter runter
    expect(btn("s2:1")).not.toContain(" disabled=\"\"")
    expect(btn("s1:-1")).not.toContain(" disabled=\"\"")
    expect(out).not.toContain("data-plan-import")
  })

  it("Leeres Studio, Atelier hat Daten: Übernahme wird angeboten", () => {
    const out = outline({ plan: EMPTY, preview: PREVIEW })
    expect(out).toContain("data-plan-import")
    expect(out).toContain('import_offer:{"scenes":"scene_count:{\\"count\\":2}","shots":"shot_count:{\\"count\\":3}","elements":"figure_count:{\\"count\\":1}"}')
    expect(outline({ plan: EMPTY, preview: { ...PREVIEW, plan_exists: true } })).not.toContain("data-plan-import")
  })

  it("Übernahme-Dialog: Mengen, Hinweis auf Kopie, eigener Knopf statt Rückfrage-Popup", () => {
    const out = html(<ImportDialog preview={PREVIEW} busy={false} onRun={noop} onClose={noop} />)
    expect(out).toContain('import_counts:{"scenes":"scene_count:{\\"count\\":2}","shots":"shot_count:{\\"count\\":3}","elements":"figure_count:{\\"count\\":1}"}')
    expect(out).toContain("import_look")
    expect(out).toContain("import_hint")
    expect(out).toContain("data-import-run")
    expect(out).toContain('role="dialog"')
  })

  it("Kopf: Werte, Seitenformate, Palette als Text", () => {
    const out = html(<HeadForm head={PLAN.screenplay} busy={false} onSave={noop} />)
    expect(out).toContain('value="Sturm"')
    expect(attr(out, "data-head-aspect")).toEqual(["16:9", "9:16", "1:1", "4:3", "21:9"])
    expect(out).toContain('value="#111, #222"')
    expect(out).toContain('value="kling"')
  })

  it("Szene: Felder, Kamera aus den Vorgaben, Bausteine zum Ankreuzen, Dialoge", () => {
    const out = html(<SceneForm scene={PLAN.scenes[0]} elements={PLAN.elements} presets={PLAN.presets} busy={false} onSave={noop} onDelete={noop} />)
    expect(out).toContain('value="Hafen"')
    expect(attr(out, "data-scene-camera")).toEqual(["shot", "lens", "light", "weather", "time", "mood"])
    expect(out).toMatch(/<option value="closeup" selected="">cam\.shot\.closeup<\/option>/)
    expect(out).toMatch(/data-scene-element="e1"[^>]*checked/)
    expect(out).not.toMatch(/data-scene-element="e2"[^>]*checked/)
    expect(out).toContain("Wo bist du?")
    expect(out).toContain("data-plan-delete")
  })

  it("Baustein: Referenzbilder über /api/files, Bilder der Bibliothek zum Hinzufügen", () => {
    const imgs = [IMG("b1", "/data/w/atelier/images/b1.png"), IMG("b2", "/data/w/atelier/images/b2.png"),
      IMG("c", "/data/w/atelier/characters/c/a.png")]                    // schon Referenz → nicht noch einmal anbieten
    const out = html(<ElementForm element={PLAN.elements[1]} base="/data/w" images={imgs} busy={false} onSave={noop} onDelete={noop} />)
    expect(out).toContain("/api/files?path=%2Fdata%2Fw%2Fatelier%2Fcharacters%2Fc%2Fa.png")
    expect(attr(out, "data-element-pick")).toEqual(["atelier/images/b1.png", "atelier/images/b2.png"])
    expect(attr(out, "data-element-kind")).toEqual(["character", "place", "object"])
    expect(out).toContain('value="Mira"')
  })

  it("Vorschau: Kopf, Szene (erstes Bild), Baustein (Referenzbild), Shot", () => {
    expect(html(<PlanPreview plan={PLAN} selection={{ kind: "head" }} />)).toContain("Ein Hafen")
    expect(html(<PlanPreview plan={PLAN} selection={{ kind: "scene", id: "s2" }} />)).toContain("%2Fdata%2Fw%2Fatelier%2Fimages%2Fa.png")
    expect(html(<PlanPreview plan={PLAN} selection={{ kind: "element", id: "e1" }} />)).toContain("%2Fatelier%2Fcharacters%2Fc%2Fa.png")
    expect(html(<PlanPreview plan={PLAN} selection={{ kind: "shot", sceneId: "s2", id: "h2" }} />)).toContain("Prompt h2")
    expect(html(<PlanPreview plan={PLAN} selection={null} />)).toContain("plan_pick")
  })

  it("Storyboard: echte Shots der gewählten Szene, ohne Szene ein Hinweis, kein Beispiel-Schild", () => {
    const out = html(<StoryboardPanel scene={PLAN.scenes[0]} base="/data/w" selected="h2" busy={null} {...SB} />)
    expect(attr(out, "data-storyboard-shot")).toEqual(["h1", "h2"])
    expect(out).toContain("%2Fdata%2Fw%2Fatelier%2Fimages%2Fa.png")
    expect(out).not.toContain("data-studio-demo-badge")
    expect(html(<StoryboardPanel scene={null} base="/data/w" selected={null} busy={null} {...SB} />)).toContain("storyboard_pick_scene")
    expect(html(<StoryboardPanel scene={PLAN.scenes[1]} base="/data/w" selected={null} busy={null} {...SB} />)).toContain("storyboard_no_shots")
  })

  it("Löschen über eigenen Dialog mit Namen", () => {
    const out = html(<DeleteDialog name="Mira" busy={false} onConfirm={noop} onClose={noop} />)
    expect(out).toContain('delete_question:{"name":"Mira"}')
    expect(out).toContain("data-delete-confirm")
    expect(out).toContain('role="dialog"')
  })
})
