import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})), put: vi.fn() } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import { FreeForm } from "./FreeForm"
import { FreeGallery } from "./FreeGallery"
import { GenerateSideBar } from "./GenerateSideBar"
import { freeImages, freeValid, shotChoices, toggleRef } from "./freeLogic"
import type { LibraryItem } from "./api"
import type { Job, Plan, Scene } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const buttons = (out: string) => [...out.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).filter(Boolean)
const scene = (id: string, title: string, shots = 0): Scene => ({ id, title, description: "", location: "", time_of_day: "", element_ids: [],
  dialogues: [], camera: {}, shots: Array.from({ length: shots }, (_, i) => ({ id: `${id}-${i}`, order: i, shot: "", prompt: `p${i}`,
    element_ids: [], duration: 3, status: "planned", image_rel: null, video_rel: null, variants: [] })) })
const PLAN = (scenes: Scene[]): Plan => ({ base: "/w", presets: {}, elements: [], scenes, screenplay: { title: "", aspect_ratio: "16:9" } as Plan["screenplay"] })
const item = (rel: string, source: LibraryItem["source"], kind: LibraryItem["kind"] = "image", created = "2026-10-18T10:00:00Z"): LibraryItem =>
  ({ id: rel, kind, origin: "ai", source, name: rel.split("/").pop() || "", rel, abs: `/w/${rel}`, size: 1, created_at: created, prompt: "kite" })
const FORM = { prompt: "", model: "", aspect: "16:9", count: 1, refs: [] as string[] }
const job = (p: Partial<Job>): Job => ({ id: "j", kind: "free_images", target: "free:x", scene_id: "", status: "running", error: null,
  result: null, created_at: "x", finished_at: null, progress: { total: 4, done: 2, failed: 0, current: "" }, ...p })

describe("B3 – Erzeugen, links: „+ Shot“ und „Freies Bild“", () => {
  it("beide Knöpfe beschriftet; „+ Shot“ ohne Szenen gesperrt", () => {
    const empty = html(<GenerateSideBar plan={PLAN([])} free={false} busy={false} onFree={noop} onAddShot={noop} />)
    expect(buttons(empty)).toEqual(["gen_add_shot", "gen_free"])
    expect(empty).toMatch(/<button[^>]*disabled=""[^>]*data-gen-add-shot/)
    const some = html(<GenerateSideBar plan={PLAN([scene("a", "Hafen"), scene("b", "Sturm")])} free busy={false} onFree={noop} onAddShot={noop} />)
    expect(some).not.toMatch(/<button[^>]*disabled=""[^>]*data-gen-add-shot/)
    expect(some).toMatch(/aria-pressed="true"[^>]*data-gen-free|data-gen-free[^>]*aria-pressed="true"/)
  })

  it("„+ Shot“ öffnet die Liste der Szenen (Klick legt dort an)", () => {
    const out = html(<GenerateSideBar plan={PLAN([scene("a", "Hafen"), scene("b", "")])} free={false} busy={false} onFree={noop}
      onAddShot={noop} pickScene />)
    expect(buttons(out)).toEqual(["gen_add_shot", "gen_free", "Hafen", "untitled"])
  })
})

describe("B3 – Freies Bild: Formular", () => {
  it("Beschreibung, Modell, Format, Anzahl 1–4, Kostenhinweis; „Bilder erzeugen“ erst mit Beschreibung", () => {
    const out = html(<FreeForm form={FORM} catalog={null} images={[]} job={null} busy={false} onChange={noop} onRun={noop} />)
    for (const k of ["free_title", "free_prompt", "free_count", "f.aspect", "free_cost"]) expect(out).toContain(k)
    expect(buttons(out)).toEqual(["1", "2", "3", "4", 'free_run:{"count":1} costs_badge'])   // C3: Zeichen „kostet“
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*data-free-run/)
    const filled = html(<FreeForm form={{ ...FORM, prompt: "kite", count: 3 }} catalog={null} images={[]} job={null} busy={false} onChange={noop} onRun={noop} />)
    expect(filled).not.toMatch(/<button[^>]*disabled=""[^>]*data-free-run/)
    expect(filled).toContain('free_run:{"count":3}')
    expect(filled).toMatch(/data-free-count="3"[^>]*aria-pressed="true"|aria-pressed="true"[^>]*data-free-count="3"/)
  })

  it("läuft: Fortschritt „2 von 4“, Knopf gesperrt; fertig mit Fehlern: Meldung", () => {
    const run = html(<FreeForm form={{ ...FORM, prompt: "x" }} catalog={null} images={[]} job={job({})} busy={false} onChange={noop} onRun={noop} />)
    expect(run).toContain('free_progress:{"done":2,"total":4}')
    const withFail = html(<FreeForm form={{ ...FORM, prompt: "x" }} catalog={null} images={[]} busy={false} onChange={noop} onRun={noop}
      job={job({ progress: { total: 4, done: 1, failed: 1, current: "" } })} />)
    expect(withFail).toContain('free_progress:{"done":2,"total":4}')                   // fehlgeschlagene zählen als erledigt
    expect(run).toMatch(/<button[^>]*disabled=""[^>]*data-free-run/)
    const failed = html(<FreeForm form={{ ...FORM, prompt: "x" }} catalog={null} images={[]} job={job({ status: "failed", error: "no_key" })} busy={false}
      onChange={noop} onRun={noop} />)
    expect(failed).toContain("job_err.no_key")
    const partly = html(<FreeForm form={{ ...FORM, prompt: "x" }} catalog={null} images={[]} busy={false} onChange={noop} onRun={noop}
      job={job({ status: "done", progress: { total: 4, done: 3, failed: 1, current: "" } })} />)
    expect(partly).toContain('free_partly:{"failed":1}')
  })

  it("Referenzbilder: nur Bilder aus der Bibliothek, höchstens 3 ankreuzbar", () => {
    const imgs = [item("a.png", "atelier"), item("b.png", "studio"), item("c.png", "studio_free"), item("d.png", "studio")]
    const out = html(<FreeForm form={{ ...FORM, prompt: "x", refs: ["a.png", "b.png", "c.png"] }} catalog={null} images={imgs} job={null} busy={false}
      onChange={noop} onRun={noop} />)
    expect((out.match(/data-free-ref="[^"]+"[^>]*aria-pressed="true"|aria-pressed="true"[^>]*data-free-ref/g) || []).length).toBe(3)
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*data-free-ref="d.png"|<button[^>]*data-free-ref="d.png"[^>]*disabled=""/)
  })

  it("Logik: gültig, Referenzen umschalten (höchstens 3)", () => {
    expect(freeValid({ ...FORM, prompt: " " })).toBe(false)
    expect(freeValid({ ...FORM, prompt: "x" })).toBe(true)
    expect(freeValid({ ...FORM, prompt: "x".repeat(2001) })).toBe(false)
    expect(freeValid({ ...FORM, prompt: "x", count: 5 })).toBe(false)
    expect(toggleRef(["a"], "a")).toEqual([])
    expect(toggleRef(["a", "b"], "c")).toEqual(["a", "b", "c"])
    expect(toggleRef(["a", "b", "c"], "d")).toEqual(["a", "b", "c"])
  })
})

describe("B3 – Galerie freier Bilder", () => {
  const free = [item("studio/media/free/old.png", "studio_free", "image", "2026-10-18T09:00:00Z"),
    item("studio/media/free/new.png", "studio_free", "image", "2026-10-18T11:00:00Z"), item("studio/media/images/s.png", "studio")]

  it("nur freie Bilder, neueste zuerst", () => {
    expect(freeImages(free).map((i) => i.rel)).toEqual(["studio/media/free/new.png", "studio/media/free/old.png"])
  })

  it("je Bild: „Einem Shot zuweisen“ (Szene · Shot N) und „Auf die Zeitleiste“; leer: Hinweis", () => {
    const plan = PLAN([scene("a", "Hafen", 2), scene("b", "Leer"), scene("c", "Sturm", 1)])
    const out = html(<FreeGallery items={free} plan={plan} busy={false} onAssign={noop} onTimeline={noop} />)
    expect((out.match(/data-free-image=/g) || []).length).toBe(2)
    expect(buttons(out).filter((b) => b === "free_timeline")).toHaveLength(2)
    expect(out).toContain('<option value="a:a-0">Hafen · shot:{"n":1}</option>')
    expect(out).toContain('<option value="c:c-0">Sturm · shot:{"n":1}</option>')
    expect(out).not.toContain("Leer ·")
    expect(out).toContain("free_assign")
    expect(html(<FreeGallery items={[]} plan={plan} busy={false} onAssign={noop} onTimeline={noop} />)).toContain("free_none")
    const noShots = html(<FreeGallery items={free} plan={PLAN([])} busy={false} onAssign={noop} onTimeline={noop} />)
    expect(noShots).toContain("free_no_shots")
    expect(buttons(noShots)).not.toContain("free_assign")                              // ohne Shots nichts zuzuweisen
    expect(noShots).not.toContain("<select")
  })

  it("Liste der Shots zum Zuweisen", () => {
    expect(shotChoices(PLAN([scene("a", "", 1)]))).toEqual([{ value: "a:a-0", scene: "", n: 1 }])
    expect(shotChoices(null)).toEqual([])
  })
})
