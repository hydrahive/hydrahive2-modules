import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o && !("defaultValue" in o) ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { jobText, latestJob } from "./jobLogic"
import type { Job, Plan, Scene, Shot } from "./planApi"
import { PlanPreview } from "./PlanPreview"
import { ShotVideo } from "./ShotVideo"
import { StoryboardPanel } from "./StoryboardPanel"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const job = (p: Partial<Job>): Job => ({ id: "j", kind: "video", target: "a", scene_id: "s", status: "running", error: null, result: null, created_at: "2026-10-17T10:00:00Z", finished_at: null, ...p })
const shot = (p: Partial<Shot> = {}): Shot => ({ id: "a", order: 0, shot: "", prompt: "p", element_ids: [], duration: 5, status: "planned", image_rel: null, video_rel: null, variants: [], ...p })

describe("Studio 3b – Video", () => {
  it("Logik: jüngster Auftrag je Art; Fehlertexte für Video-Codes", () => {
    const jobs = [job({ id: "bild", kind: "image", status: "done", created_at: "2026-10-17T12:00:00Z" }), job({ id: "vid", kind: "video", status: "failed", error: "timeout" })]
    expect(latestJob(jobs, "a", "video")?.id).toBe("vid")
    expect(latestJob(jobs, "a", "image")?.id).toBe("bild")
    expect(latestJob(jobs, "b", "video")).toBeNull()
    const t = (k: string) => `T:${k}`
    for (const code of ["timeout", "video_failed", "too_big", "bad_video", "bad_url", "image_gone"]) expect(jobText(t, job({ status: "failed", error: code }))).toBe(`T:job_err.${code}`)
  })

  it("Ohne Bild: Knopf gesperrt mit Hinweis", () => {
    const out = html(<ShotVideo shot={shot()} base="/w" job={null} onGenerate={noop} />)
    expect(out.match(/<button[^>]*data-shot-video-generate[^>]*>/)?.[0]).toContain(' disabled=""')
    expect(out).toContain("video_needs_image")
  })

  it("Mit Bild: „Video erzeugen“ und Dauer; läuft: gesperrt + Ladeanzeige; Fehler: Meldung", () => {
    const s = shot({ image_rel: "studio/media/images/1.png", status: "image_ready", duration: 6 })
    const out = html(<ShotVideo shot={s} base="/w" job={null} onGenerate={noop} />)
    expect(out.match(/<button[^>]*data-shot-video-generate[^>]*>/)?.[0]).not.toContain(' disabled=""')
    expect(out).toContain('video_generate:{"seconds":6}')
    const run = html(<ShotVideo shot={s} base="/w" job={job({ status: "running" })} onGenerate={noop} />)
    expect(run.match(/<button[^>]*data-shot-video-generate[^>]*>/)?.[0]).toContain(' disabled=""')
    expect(run).toContain("video_running")
    const bad = html(<ShotVideo shot={{ ...s, status: "failed" }} base="/w" job={job({ status: "failed", error: "timeout" })} onGenerate={noop} />)
    expect(bad).toContain("data-shot-video-error")
    expect(bad).toContain("job_err.timeout")
  })

  it("Fertig: Video-Player über /api/files, Knopf „Neues Video“", () => {
    const s = shot({ image_rel: "studio/media/images/1.png", video_rel: "studio/media/videos/v.mp4", status: "done" })
    const out = html(<ShotVideo shot={s} base="/w" job={job({ status: "done" })} onGenerate={noop} />)
    expect(out).toMatch(/<video[^>]*src="\/api\/files\?path=%2Fw%2Fstudio%2Fmedia%2Fvideos%2Fv\.mp4/)
    expect(out).toContain("video_again")
  })

  it("Vorschau Mitte: Shot mit Video spielt das Video (mit Bild als Standbild)", () => {
    const s = shot({ image_rel: "studio/media/images/1.png", video_rel: "studio/media/videos/v.mp4", status: "done" })
    const scene: Scene = { id: "s", title: "S", description: "", location: "", time_of_day: "", element_ids: [], dialogues: [], camera: {}, shots: [s] }
    const plan = { base: "/w", screenplay: {}, scenes: [scene], elements: [], presets: {} } as unknown as Plan
    const out = html(<PlanPreview plan={plan} selection={{ kind: "shot", sceneId: "s", id: "a" }} />)
    expect(out).toMatch(/<video[^>]*src="\/api\/files\?path=%2Fw%2Fstudio%2Fmedia%2Fvideos%2Fv\.mp4/)
    expect(out).toMatch(/poster="\/api\/files\?path=%2Fw%2Fstudio%2Fmedia%2Fimages%2F1\.png/)
  })

  it("Storyboard: Karte zeigt ein Video-Zeichen, wenn der Shot ein Video hat", () => {
    const scene: Scene = { id: "s", title: "S", description: "", location: "", time_of_day: "", element_ids: [], dialogues: [], camera: {},
      shots: [shot({ id: "a", video_rel: "studio/media/videos/v.mp4", status: "done" }), shot({ id: "b" })] }
    const out = html(<StoryboardPanel scene={scene} base="/w" selected={null} busy={null} onSelect={noop} onAdd={noop} onMove={noop} onDecompose={noop} />)
    expect([...out.matchAll(/data-storyboard-video="([^"]+)"/g)].map((m) => m[1])).toEqual(["a"])
  })
})
