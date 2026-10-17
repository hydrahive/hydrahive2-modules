import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o && !("defaultValue" in o) ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { DecomposeDialog } from "./DecomposeDialog"
import type { PlanElement, Scene, Shot } from "./planApi"
import { hasMedia, moveShot, sceneDuration } from "./planLogic"
import { ShotForm } from "./ShotForm"
import { StoryboardPanel } from "./StoryboardPanel"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const attr = (out: string, name: string) => [...out.matchAll(new RegExp(`${name}="([^"]+)"`, "g"))].map((m) => m[1])
const SB = { onSelect: noop, onAdd: noop, onMove: noop, onDecompose: noop }
const shot = (id: string, p: Partial<Shot> = {}): Shot => ({ id, order: 0, shot: "wide", prompt: `P ${id}`, element_ids: [], duration: 5, status: "planned", image_rel: null, video_rel: null, variants: [], ...p })
const el = (id: string, name: string): PlanElement => ({ id, kind: "character", name, description: "", style_anchor: "", palette: [], references: [] })
const SCENE: Scene = { id: "s1", title: "Hafen", description: "", location: "", time_of_day: "", element_ids: ["e1"], dialogues: [], camera: {},
  shots: [shot("a", { duration: 6 }), shot("b", { duration: 4, image_rel: "x.png" }), shot("c", { duration: 3 })] }

describe("Studio 2b – Shots", () => {
  it("Logik: Shot verschieben, Gesamtdauer, Medien erkennen", () => {
    expect(moveShot(["a", "b", "c"], "b", 1)).toEqual(["a", "c", "b"])
    expect(moveShot(["a", "b", "c"], "a", -1)).toEqual(["a", "b", "c"])
    expect(sceneDuration(SCENE)).toBe(13)
    expect(sceneDuration(null)).toBe(0)
    expect(hasMedia(SCENE)).toBe(true)
    expect(hasMedia({ ...SCENE, shots: [shot("a"), shot("v", { video_rel: "v.mp4" })] })).toBe(true)
    expect(hasMedia({ ...SCENE, shots: [shot("a")] })).toBe(false)
  })

  it("Storyboard: Gesamtdauer, Zerlegen-Knopf, +, Pfeile mit gesperrten Rändern", () => {
    const out = html(<StoryboardPanel scene={SCENE} base="/w" selected="b" busy={null} {...SB} />)
    expect(out).toContain('scene_duration:{"seconds":13}')
    expect(out).toContain("data-storyboard-decompose")
    expect(out).toContain("data-storyboard-add")
    const btn = (k: string) => out.match(new RegExp(`<button[^>]*data-storyboard-move="${k}"[^>]*>`))?.[0] ?? ""
    expect(btn("a:-1")).toContain(' disabled=""')
    expect(btn("c:1")).toContain(' disabled=""')
    expect(btn("b:-1")).not.toContain(' disabled=""')
    expect(btn("b:1")).not.toContain(' disabled=""')
  })

  it("Storyboard: während der Zerlegung gesperrt mit Ladeanzeige; leere Szene bietet Zerlegen an", () => {
    const out = html(<StoryboardPanel scene={SCENE} base="/w" selected={null} busy="decompose" {...SB} />)
    expect(out.match(/<button[^>]*data-storyboard-decompose[^>]*>/)?.[0]).toContain(' disabled=""')
    expect(out).toContain("decompose_running")
    const empty = html(<StoryboardPanel scene={{ ...SCENE, shots: [] }} base="/w" selected={null} busy={null} {...SB} />)
    expect(empty).toContain("storyboard_no_shots")
    expect(empty).toContain("data-storyboard-decompose")
    expect(html(<StoryboardPanel scene={null} base="/w" selected={null} busy={null} {...SB} />)).not.toContain("data-storyboard-decompose")
  })

  it("Shot-Formular: Kamera aus Vorgaben, nur Bausteine der Szene, Dauer, Löschen; Status nur lesbar", () => {
    const out = html(<ShotForm shot={shot("a", { shot: "closeup", element_ids: ["e1"], status: "image_ready" })} index={0}
      elements={[el("e1", "Mira"), el("e2", "Ole")]} sceneElementIds={["e1"]} presets={["closeup", "wide"]} busy={false} onSave={noop} onDelete={noop} />)
    expect(out).toMatch(/<option value="closeup" selected="">cam\.shot\.closeup<\/option>/)
    expect(attr(out, "data-shot-element")).toEqual(["e1"])
    expect(out).toMatch(/data-shot-element="e1"[^>]*checked/)
    expect(out).toContain('value="5"')
    expect(out).toContain("shot_status.image_ready")
    expect(out).not.toMatch(/<select[^>]*data-field="status"/)
    expect(out).toContain("data-plan-delete")
    expect(out).toContain("P a")
  })

  it("Rückfrage vor dem Ersetzen: Anzahl, Hinweis Bibliothek, eigener Knopf", () => {
    const out = html(<DecomposeDialog count={3} busy={false} onConfirm={noop} onClose={noop} />)
    expect(out).toContain('decompose_replace_question:{"count":3}')
    expect(out).toContain("decompose_replace_hint")
    expect(out).toContain("data-decompose-confirm")
    expect(out).toContain('role="dialog"')
  })
})
