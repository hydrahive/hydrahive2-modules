import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})), put: vi.fn(() => new Promise(() => {})) } }))
import { castToggle, faceOf, imageCards, missingImages, shotBusy, variantStep } from "./neu/guidedLogic"
import { ImageCard } from "./neu/ImageCard"
import { ImagesHead } from "./neu/StepImagesLive"
import type { Job, Plan, PlanElement, Scene, Shot } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const buttons = (out: string) => [...out.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).filter(Boolean)
const shot = (o: Partial<Shot> = {}): Shot => ({ id: "x1", order: 0, shot: "", prompt: "Bild", element_ids: [], duration: 5, status: "planned",
  image_rel: null, video_rel: null, variants: [], cast: [], excluded_ids: [], ...o })
const scene = (o: Partial<Scene> = {}): Scene => ({ id: "s1", title: "Wald", description: "Hydra im Wald", location: "", time_of_day: "",
  element_ids: [], dialogues: [], camera: {}, shots: [shot()], ...o })
const el = (o: Partial<PlanElement> = {}): PlanElement => ({ id: "h", kind: "character", name: "Hydra", description: "", style_anchor: "",
  palette: [], references: [], probe_rel: "", approved: false, no_photo: false, ...o })
const job = (o: Partial<Job>): Job => ({ id: "j", kind: "image", target: "x1", scene_id: "s1", status: "running", error: null, result: null,
  created_at: "2026-10-19T10:00:00Z", finished_at: null, ...o })
const plan = (scenes: Scene[], elements: PlanElement[] = []): Plan => ({ base: "/w", presets: {}, elements, scenes,
  screenplay: { title: "", logline: "", description: "", aspect_ratio: "16:9", default_duration: 5, models: { image: "m/bild" } as Plan["screenplay"]["models"],
    look: { style: "", palette: [] }, scene_order: scenes.map((s) => s.id) } })

describe("G3 – Logik", () => {
  it("Karten: eine je Shot; eine Szene mit einem Shot → Szenentext; mehrere → „Teil N“ und Bildbeschreibung", () => {
    const p = plan([scene(), scene({ id: "s2", description: "Schnee", shots: [shot({ id: "a", prompt: "A" }), shot({ id: "b", prompt: "B" })] }), scene({ id: "s3", shots: [] })])
    expect(imageCards(p).map((c) => [c.n, c.part, c.text, c.shot.id])).toEqual([[1, 0, "Hydra im Wald", "x1"], [2, 1, "A", "a"], [2, 2, "B", "b"]])
    expect(imageCards(null)).toEqual([])
    expect(imageCards(plan([scene({ description: "", title: "Nur Titel" })]))[0].text).toBe("Nur Titel")
  })

  it("fehlende Bilder zählen", () => {
    expect(missingImages(plan([scene(), scene({ id: "s2", shots: [shot({ id: "b", image_rel: "a.png" })] })]))).toBe(1)
  })

  it("läuft: eigener Bild-Auftrag oder Sammelauftrag gerade an diesem Shot", () => {
    expect(shotBusy([job({})], "x1")).toBe(true)
    expect(shotBusy([job({ status: "done" })], "x1")).toBe(false)
    expect(shotBusy([job({ target: "y" })], "x1")).toBe(false)
    expect(shotBusy([job({ kind: "video" })], "x1")).toBe(false)
    expect(shotBusy([job({ kind: "images_all", target: "batch:p", progress: { total: 2, done: 0, failed: 0, current: "", current_shot: "x1" } })], "x1")).toBe(true)
    expect(shotBusy([job({ kind: "images_all", target: "batch:p", status: "done", progress: { total: 2, done: 2, failed: 0, current: "", current_shot: "x1" } })], "x1")).toBe(false)
    expect(shotBusy([job({ kind: "images_all", target: "batch:p", progress: { total: 2, done: 0, failed: 0, current: "", current_shot: "anderer" } })], "x1")).toBe(false)
  })

  it("Blättern: zyklisch durch die Varianten", () => {
    const s = shot({ variants: ["a", "b", "c"], image_rel: "b" })
    expect(variantStep(s, 1)).toBe("c")
    expect(variantStep(s, -1)).toBe("a")
    expect(variantStep(shot({ variants: ["a", "b", "c"], image_rel: "c" }), 1)).toBe("a")
    expect(variantStep(shot({ variants: ["a"], image_rel: "a" }), 1)).toBeNull()
    expect(variantStep(shot({ variants: ["a", "b"], image_rel: "zz" }), 1)).toBe("a")
    expect(variantStep(shot({ variants: ["a", "b", "c"], image_rel: "zz" }), -1)).toBe("a")          // unbekannt → das erste
  })

  it("Mit dabei an/aus (H2: im Bild = angehakt): weg → abgehakt; dazu → angehakt und nicht mehr ausgeschlossen", () => {
    expect(castToggle(shot({ cast: ["h"], element_ids: ["h"] }), "h")).toEqual({ element_ids: [], excluded_ids: [] })
    expect(castToggle(shot({ cast: [], excluded_ids: ["h"] }), "h")).toEqual({ element_ids: ["h"], excluded_ids: [] })
    expect(castToggle(shot({ cast: [] }), "m")).toEqual({ element_ids: ["m"], excluded_ids: [] })
  })

  it("Gesicht: Probebild nur wenn freigegeben, sonst Foto, sonst nichts", () => {
    expect(faceOf(el({ probe_rel: "p.png", approved: true, references: ["f.png"] }))).toBe("p.png")
    expect(faceOf(el({ probe_rel: "p.png", references: ["f.png"] }))).toBe("f.png")
    expect(faceOf(el({}))).toBe("")
  })
})

const card = (s: Shot, jobs: Job[] = [], format = "16:9") => html(<ImageCard card={{ n: 2, part: 0, text: "Hydra im Wald", sceneId: "s1", shot: s }}
  base="/w" format={format} elements={[el(), el({ id: "m", name: "Mira" })]} jobs={jobs} busy={false} model="m/bild"
  onMake={noop} onFlip={noop} onDrop={noop} onCast={noop} onChange={noop} />)

describe("G3 – Oberfläche", () => {
  it("ohne Bild: „Noch kein Bild“, „Bild machen“ (kostet), Nummer + Text", () => {
    const out = card(shot())
    expect(out).toContain("guided.no_image")
    expect(buttons(out)).toContain("guided.make_image costs_badge")
    expect(out).toContain("costs_hint:{\"model\":\"m/bild\"}")
    expect(out).toContain(">2<")
    expect(out).toContain("Hydra im Wald")
  })

  it("mit Bildern: gezeigt wird das gewählte, Pfeile + „Bild X von N“, „Anderes Bild machen“, „Dieses Bild wegwerfen“", () => {
    const out = card(shot({ image_rel: "studio/media/images/b.png", variants: ["studio/media/images/a.png", "studio/media/images/b.png"] }))
    expect(out).toContain('src="/f/w/studio/media/images/b.png"')
    expect(out).toContain("guided.image_n:{\"n\":2,\"count\":2}")
    expect(out).toContain('aria-label="guided.prev_image"')
    expect(buttons(out)).toEqual(expect.arrayContaining(["guided.another_image costs_badge", "guided.drop_image"]))
    const one = card(shot({ image_rel: "studio/media/images/a.png", variants: ["studio/media/images/a.png"] }))
    expect(one).not.toContain("guided.prev_image")
  })

  it("Hochformat: Bild im Hochformat", () => {
    expect(card(shot(), [], "9:16")).toContain("aspect-[9/16]")
    expect(card(shot())).toContain("aspect-video")
  })

  it("läuft: Schleier; Fehler: Text + „Noch einmal versuchen“", () => {
    expect(card(shot(), [job({})])).toContain("guided.image_busy")
    const out = card(shot(), [job({ status: "failed", error: "no_key" })])
    expect(out).toContain("job_err.no_key")
    expect(buttons(out)).toContain("guided.image_retry costs_badge")
    // ein altes fehlgeschlagenes Bild stört nicht mehr, sobald eins da ist
    const later = card(shot({ image_rel: "studio/media/images/a.png", variants: ["studio/media/images/a.png"] }), [job({ status: "failed", error: "no_key" })])
    expect(later).not.toContain("job_err.no_key")
  })

  it("Mit dabei: alle Figuren, angehakte gedrückt, Namen sichtbar", () => {
    const out = card(shot({ cast: ["h"] }))
    expect(out).toContain("guided.with")
    expect(out).toMatch(/aria-pressed="true"[^>]*>.*?Hydra/s)
    expect(out).toMatch(/aria-pressed="false"[^>]*>.*?Mira/s)
  })

  it("Kopf: Sammelknopf je nach Stand, Fortschritt mit Anhalten", () => {
    const head = (open: number, total: number, batch: Job | null = null) => html(<ImagesHead open={open} total={total} batch={batch} model="m/bild" busy={false} onAll={noop} onStop={noop} />)
    expect(buttons(head(3, 3))).toEqual(["guided.all_images costs_badge"])
    expect(buttons(head(2, 3))).toEqual(["guided.missing_images:{\"count\":2} costs_badge"])
    expect(buttons(head(0, 3))).toEqual([])
    const run = head(2, 3, job({ kind: "images_all", target: "batch:p", progress: { total: 2, done: 1, failed: 0, current: "Wald" } }))
    expect(run).toContain("guided.batch_progress:{\"done\":1,\"total\":2}")
    expect(buttons(run)).toEqual(["guided.stop"])
  })
})
