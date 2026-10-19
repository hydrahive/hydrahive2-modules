import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})), put: vi.fn(() => new Promise(() => {})) } }))
import { filmBody, filmCosts, filmNotes, previewFrames } from "./neu/guidedLogic"
import { FilmPanel } from "./neu/StepFilmLive"
import type { Job, Plan, Scene, Shot } from "./planApi"
import type { RenderItem } from "./renderApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const buttons = (out: string) => [...out.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).filter(Boolean)
const shot = (o: Partial<Shot> = {}): Shot => ({ id: "x1", order: 0, shot: "", prompt: "p", element_ids: [], duration: 4, status: "planned",
  image_rel: "studio/media/images/a.png", video_rel: null, variants: [], ...o })
const scene = (o: Partial<Scene> = {}): Scene => ({ id: "s1", title: "T", description: "Eins", location: "", time_of_day: "", element_ids: [],
  dialogues: [], camera: {}, shots: [shot()], ...o })
const plan = (scenes: Scene[]): Plan => ({ base: "/w", presets: {}, elements: [], scenes,
  screenplay: { title: "", logline: "", description: "", aspect_ratio: "16:9", default_duration: 5,
    models: { music: "m/musik", voice: "" } as Plan["screenplay"]["models"], look: { style: "", palette: [] }, scene_order: scenes.map((s) => s.id) } })
const film = (o: Partial<RenderItem> = {}): RenderItem => ({ rel: "studio/renders/a.mp4", abs: "/w/studio/renders/a.mp4", name: "a.mp4", duration: 12,
  width: 1280, height: 720, created_at: "2026-10-19T12:00:00Z", missing: 0, clips: 3, ...o })
const job = (o: Partial<Job>): Job => ({ id: "j", kind: "film", target: "film:p", scene_id: "", status: "running", error: null, result: null,
  created_at: "2026-10-19T10:00:00Z", finished_at: null, progress: { total: 5, done: 2, failed: 0, current: "music" }, ...o })

describe("G5 – Logik", () => {
  it("Vorschau: je Szene Clip, sonst Bild; ohne Bild übersprungen", () => {
    const p = plan([scene(), scene({ id: "s2", shots: [shot({ id: "b", video_rel: "v.mp4" })] }), scene({ id: "s3", shots: [shot({ id: "c", image_rel: null })] })])
    expect(previewFrames(p).map((f) => [f.kind, f.rel, f.seconds])).toEqual([["image", "studio/media/images/a.png", 4], ["video", "v.mp4", 4]])
    expect(previewFrames(null)).toEqual([])
  })

  it("Auftrag: nur die drei Schalter, rebuild nur wenn gesetzt", () => {
    expect(filmBody({ music: true, voice: false, subtitles: true })).toEqual({ music: true, voice: false, subtitles: true })
    expect(filmBody({ music: false, voice: false, subtitles: false }, true)).toEqual({ music: false, voice: false, subtitles: false, rebuild: true })
    expect(filmBody({ music: false, voice: false, subtitles: false }, false).rebuild).toBe(false)
  })

  it("Kosten: Modelle von Musik/Stimme nur wenn gewählt", () => {
    const p = plan([])
    expect(filmCosts(p, { music: true, voice: true, subtitles: true })).toEqual(["m/musik", ""])
    expect(filmCosts(p, { music: false, voice: true, subtitles: false })).toEqual([""])
    expect(filmCosts(p, { music: false, voice: false, subtitles: true })).toEqual([])
  })

  it("Hinweise aus dem Ergebnis", () => {
    expect(filmNotes(job({ status: "done", result: { notes: ["music_failed"], voice_failed: 2 } }))).toEqual(["music_failed", "voice_failed"])
    expect(filmNotes(job({ status: "done", result: { notes: [], voice_failed: 0 } }))).toEqual([])
    expect(filmNotes(null)).toEqual([])
    expect(filmNotes(job({ status: "running", result: { notes: ["music_failed"], voice_failed: 1 } }))).toEqual([])   // nur fertige
  })
})

const panel = (o: Partial<Parameters<typeof FilmPanel>[0]> = {}) => html(<FilmPanel films={[]} job={null} extras={{ music: true, voice: false, subtitles: true }}
  costs={["m/musik"]} busy={false} base="/w" onExtras={noop} onMake={noop} onStop={noop} {...o} />)

describe("G5 – Oberfläche", () => {
  it("Schalter Musik/Erzählstimme/Untertitel, „Film erzeugen“ mit kostet", () => {
    const out = panel()
    expect(out.match(/type="checkbox"/g)?.length).toBe(3)
    expect(out).toContain("guided.music_label")
    expect(out).toContain("guided.voice_label")
    expect(out).toContain("guided.subs_label")
    expect(buttons(out)).toContain("guided.make_film costs_badge")
    expect(buttons(panel({ costs: [] }))).toContain("guided.make_film")
  })

  it("läuft: Schritt-Anzeige + Anhalten, kein zweiter Start", () => {
    const out = panel({ job: job({}) })
    expect(out).toContain("guided.film_step.music")
    expect(out).toContain("guided.film_n:{\"done\":2,\"total\":5}")
    expect(buttons(out)).toEqual(["guided.stop"])
  })

  it("fertig: Film mit Steuerung, „Film herunterladen“, frühere Filme", () => {
    const out = panel({ films: [film(), film({ rel: "studio/renders/b.mp4", abs: "/w/studio/renders/b.mp4", name: "b.mp4" })] })
    expect(out).toMatch(/<video[^>]*controls[^>]*src="\/f\/w\/studio\/renders\/a\.mp4"|<video[^>]*src="\/f\/w\/studio\/renders\/a\.mp4"[^>]*controls/)
    expect(out).toMatch(/<a[^>]*download[^>]*>.*guided\.download/s)
    expect(out).toContain("guided.earlier:{\"count\":1}")
    expect(buttons(out)).toContain("guided.make_film_again costs_badge")
  })

  it("Fehler und Hinweise verständlich", () => {
    const out = panel({ job: job({ status: "failed", error: "render_failed" }) })
    expect(out).toContain("job_err.render_failed")
    const notes = panel({ films: [film()], job: job({ status: "done", result: { notes: ["music_failed", "no_speech"], voice_failed: 1 } }) })
    expect(notes).toContain("guided.note.music_failed")
    expect(notes).toContain("guided.note.no_speech")
    expect(notes).toContain("guided.note.voice_failed")
  })
})
