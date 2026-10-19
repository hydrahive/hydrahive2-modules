import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})), put: vi.fn(() => new Promise(() => {})) } }))
import { doneSteps, motionLeft, motionState } from "./neu/guidedLogic"
import { ClipCard } from "./neu/ClipCard"
import { ClipsHead } from "./neu/StepClipsLive"
import type { Job, Plan, Scene, Shot } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const buttons = (out: string) => [...out.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).filter(Boolean)
const shot = (o: Partial<Shot> = {}): Shot => ({ id: "x1", order: 0, shot: "", prompt: "p", element_ids: [], duration: 4, status: "planned",
  image_rel: "studio/media/images/a.png", video_rel: null, variants: [], still: false, ...o })
const scene = (o: Partial<Scene> = {}): Scene => ({ id: "s1", title: "T", description: "Hydra im Schnee", location: "", time_of_day: "", element_ids: [],
  dialogues: [], camera: {}, shots: [shot()], ...o })
const job = (o: Partial<Job>): Job => ({ id: "j", kind: "video", target: "x1", scene_id: "s1", status: "running", error: null, result: null,
  created_at: "2026-10-19T10:00:00Z", finished_at: null, ...o })
const plan = (scenes: Scene[]): Plan => ({ base: "/w", presets: {}, elements: [], scenes,
  screenplay: { title: "", logline: "", description: "", aspect_ratio: "16:9", default_duration: 5, models: { video: "m/video" } as Plan["screenplay"]["models"],
    look: { style: "", palette: [] }, scene_order: scenes.map((s) => s.id) } })

describe("G4 – Logik", () => {
  it("Zustand: ohne Bild, offen, Standbild, bewegt", () => {
    expect(motionState(shot({ image_rel: null }))).toBe("no_image")
    expect(motionState(shot())).toBe("open")
    expect(motionState(shot({ still: true }))).toBe("still")
    expect(motionState(shot({ video_rel: "v.mp4" }))).toBe("moving")
    expect(motionState(shot({ video_rel: "v.mp4", still: true }))).toBe("moving")       // Video gewinnt
    expect(motionState(shot({ video_rel: "v.mp4", image_rel: null }))).toBe("moving")  // Bild gelöscht, Clip noch da
  })

  it("übrig = mit Bild, ohne Video, kein Standbild", () => {
    const p = plan([scene(), scene({ id: "s2", shots: [shot({ id: "b", still: true })] }), scene({ id: "s3", shots: [shot({ id: "c", video_rel: "v" })] }),
      scene({ id: "s4", shots: [shot({ id: "d", image_rel: null })] })])
    expect(motionLeft(p)).toBe(1)
  })

  it("Haken Schritt 4: jede Szene bewegt oder Standbild", () => {
    expect(doneSteps(plan([scene({ shots: [shot({ video_rel: "v" })] }), scene({ id: "s2", shots: [shot({ id: "b", still: true })] })]))[4]).toBe(true)
    expect(doneSteps(plan([scene({ shots: [shot({ video_rel: "v" })] }), scene({ id: "s2", shots: [shot({ id: "b" })] })]))[4]).toBe(false)
    expect(doneSteps(plan([scene({ shots: [shot({ still: true, image_rel: null })] })]))[4]).toBe(false)     // Standbild ohne Bild zählt nicht
  })
})

const card = (s: Shot, jobs: Job[] = []) => html(<ClipCard card={{ n: 1, part: 0, text: "Hydra im Schnee", sceneId: "s1", shot: s }}
  base="/w" format="16:9" jobs={jobs} busy={false} model="m/video" onMove={noop} onStill={noop} onDrop={noop} />)

describe("G4 – Oberfläche", () => {
  it("offen: Bild, „Bewegen“ (kostet), „Als Standbild lassen“", () => {
    const out = card(shot())
    expect(out).toContain('src="/f/w/studio/media/images/a.png"')
    expect(buttons(out)).toEqual(["guided.move costs_badge", "guided.keep_still"])
    expect(out).toContain("costs_hint:{\"model\":\"m/video\"}")
  })

  it("bewegt: Video stumm in Schleife, Schild, „Neu bewegen“ + „Bewegung wegwerfen“", () => {
    const out = card(shot({ video_rel: "studio/media/videos/v.mp4" }))
    expect(out).toMatch(/<video[^>]*src="\/f\/w\/studio\/media\/videos\/v\.mp4"/)
    expect(out).toMatch(/<video[^>]*muted/)
    expect(out).toMatch(/<video[^>]*loop/)
    expect(out).toContain("guided.moving_badge")
    expect(buttons(out)).toEqual(["guided.move_again costs_badge", "guided.drop_motion"])
  })

  it("Standbild: Schild mit Dauer, „Doch bewegen“", () => {
    const out = card(shot({ still: true }))
    expect(out).toContain("guided.still_badge:{\"n\":4}")
    expect(buttons(out)).toEqual(["guided.move_anyway costs_badge"])
  })

  it("ohne Bild: Hinweis, keine Knöpfe", () => {
    const out = card(shot({ image_rel: null }))
    expect(out).toContain("guided.need_image")
    expect(out).not.toContain("<button")
    expect(out).not.toContain('class="flex flex-wrap gap-2"')                          // keine leere Knopfzeile
  })

  it("läuft: Hinweis; Fehler: Text + Knöpfe bleiben", () => {
    expect(card(shot(), [job({})])).toContain("guided.motion_busy")
    const out = card(shot(), [job({ status: "failed", error: "video_failed" })])
    expect(out).toContain("job_err.video_failed")
    expect(buttons(out)).toContain("guided.move costs_badge")
    // altes fehlgeschlagenes Video stört nicht, wenn inzwischen eins da ist
    expect(card(shot({ video_rel: "studio/media/videos/v.mp4" }), [job({ status: "failed", error: "video_failed" })])).not.toContain("job_err.video_failed")
  })

  it("Kopf: Sammelknopf je nach Stand, Fortschritt mit Anhalten", () => {
    const head = (left: number, total: number, batch: Job | null = null) => html(<ClipsHead left={left} total={total} batch={batch} model="m/video" busy={false} onAll={noop} onStop={noop} />)
    expect(buttons(head(3, 3))).toEqual(["guided.all_motion costs_badge"])
    expect(buttons(head(2, 3))).toEqual(["guided.rest_motion:{\"count\":2} costs_badge"])
    expect(buttons(head(0, 3))).toEqual([])
    expect(buttons(head(1, 3, job({ kind: "videos_all", target: "batch:p", progress: { total: 1, done: 0, failed: 0, current: "" } })))).toEqual(["guided.stop"])
  })
})
