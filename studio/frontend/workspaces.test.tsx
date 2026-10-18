import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { GenerateHint } from "./GenerateHint"
import { ShotList } from "./ShotList"
import { shotCounts, shotState } from "./shotListLogic"
import { StudioPage } from "./StudioPage"
import type { Job, Plan, Shot } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const attr = (out: string, name: string) => [...out.matchAll(new RegExp(`${name}="([^"]+)"`, "g"))].map((m) => m[1])
const shot = (p: Partial<Shot>): Shot => ({ id: "s", order: 0, shot: "", prompt: "", element_ids: [], duration: 4, status: "planned",
  image_rel: null, video_rel: null, variants: [], ...p })
const job = (p: Partial<Job>): Job => ({ id: "j", kind: "image", target: "s", scene_id: "", status: "done", error: null, result: null,
  created_at: "2026-10-17T10:00:00.000001Z", finished_at: null, ...p })
const PLAN: Plan = {
  base: "/w/p", presets: {},
  screenplay: { title: "Nordwind" } as Plan["screenplay"], elements: [],
  scenes: [
    { id: "A", title: "Hafen", description: "", location: "", time_of_day: "", element_ids: [], dialogues: [], camera: {}, shots: [
      shot({ id: "a1", prompt: "Boot legt an", image_rel: "studio/media/images/a1.jpg", video_rel: "studio/media/videos/a1.mp4" }),
      shot({ id: "a2", image_rel: "studio/media/images/a2.jpg" }),
    ] },
    { id: "B", title: "", description: "", location: "", time_of_day: "", element_ids: [], dialogues: [], camera: {}, shots: [
      shot({ id: "b1" }), shot({ id: "b2" }),
    ] },
  ],
}

describe("Reiter „Erzeugen“ – Shot-Liste", () => {
  it("Stand je Shot: Video > Bild > ohne; laufender oder fehlgeschlagener Auftrag hat Vorrang", () => {
    const [a1, a2] = PLAN.scenes[0].shots
    const [b1, b2] = PLAN.scenes[1].shots
    expect(shotState(a1, [])).toBe("video")
    expect(shotState(a2, [])).toBe("image")
    expect(shotState(b1, [])).toBe("none")
    expect(shotState(b1, [job({ target: "b1", status: "running" })])).toBe("running")
    expect(shotState(b1, [job({ target: "b1", status: "queued" })])).toBe("running")
    expect(shotState(b2, [job({ target: "b2", status: "failed", error: "no_key" })])).toBe("failed")
    expect(shotState(a2, [job({ target: "a2", status: "failed" }), job({ id: "k", target: "a2", status: "done", created_at: "2026-10-17T11:00:00Z" })])).toBe("image")
    expect(shotState(a2, [job({ target: "andere", status: "running" })])).toBe("image")   // fremder Auftrag zählt nicht
  })

  it("Zähler: mit Bild / mit Video / gesamt", () => {
    expect(shotCounts(PLAN)).toEqual({ total: 4, image: 2, video: 1 })
    expect(shotCounts(null)).toEqual({ total: 0, image: 0, video: 0 })
  })

  it("Liste nach Szenen, mit Stand und Zählern; Auswahl markiert", () => {
    const out = html(<ShotList plan={PLAN} jobs={[job({ target: "b1", status: "running" })]} selected="a2" onSelect={noop} onPlan={noop} />)
    expect(attr(out, "data-gen-shot")).toEqual(["a1", "a2", "b1", "b2"])
    expect(attr(out, "data-gen-state")).toEqual(["video", "image", "running", "none"])
    expect(attr(out, "data-gen-scene")).toEqual(["A", "B"])
    expect(out).toContain('gen_counts:{"image":2,"video":1,"total":4}')
    expect(out).toContain("Hafen")
    expect(out).toContain("untitled")                                   // Szene ohne Titel
    expect(out).toMatch(/data-gen-shot="a2"[^>]*aria-pressed="true"/)
    expect(out).toContain("/api/files?path=%2Fw%2Fp%2Fstudio%2Fmedia%2Fimages%2Fa1.jpg")   // kleines Bild
  })

  it("ohne Shots: Hinweis mit Knopf „Zum Planen“", () => {
    const out = html(<ShotList plan={{ ...PLAN, scenes: [] }} jobs={[]} selected={null} onSelect={noop} onPlan={noop} />)
    expect(out).toContain("gen_no_shots")
    expect(out).toContain("data-gen-to-plan")
    expect(attr(out, "data-gen-shot")).toEqual([])
  })

  it("rechts ohne Auswahl: Hinweis statt gesperrter Felder", () => {
    const out = html(<GenerateHint />)
    expect(out).toContain("gen_pick_shot")
    expect(out).not.toMatch(/disabled/)
  })
})

describe("Alle Reiter sind echt – keine Beispiele, kein „kommt noch“ (Untertitel seit 6a)", () => {
  it("es gibt keinen „kommt noch“-Platzhalter mehr", async () => {
    const files = import.meta.glob(["./*.tsx", "!./*.test.tsx"], { query: "?raw", import: "default", eager: true })
    expect(Object.keys(files).some((f) => f.includes("ComingSoon"))).toBe(false)
    expect(Object.values(files).join("\n")).not.toContain("data-studio-soon")
  })

  it("Studio startet ohne Beispieldaten (kein „Nordwind“, kein Beispiel-Hinweis)", () => {
    const out = html(<StudioPage />)
    expect(out).not.toContain("data-studio-demo-badge")
    expect(out).not.toContain("Titel: Nordwind")
  })

  it("Beispieldaten-Dateien sind entfernt", async () => {
    const mods = import.meta.glob("./{demoData,TimelinePanel,TrackRow,InspectorPanel}.ts{,x}")
    expect(Object.keys(mods)).toEqual([])
  })
})
