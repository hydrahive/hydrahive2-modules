import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})) } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import { DeliverPanel } from "./DeliverPanel"
import { deliverSummary, filmSize, minutes } from "./deliverLogic"
import type { Job } from "./planApi"
import type { RenderItem } from "./renderApi"
import type { TimelineClip } from "./timelineApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const buttons = (out: string) => [...out.matchAll(/<button[^>]*>(.*?)<\/button>/gs)].map((m) => m[1].replace(/<[^>]+>/g, "").trim()).filter(Boolean)
const c = (kind: TimelineClip["kind"], start: number, len: number, missing = false): TimelineClip =>
  ({ id: `${kind}${start}`, kind, start, in: 0, out: len, media_rel: kind === "placeholder" ? "" : "x", scene_id: "", shot_id: "", label: "l", ...(missing ? { missing } : {}) })
const R = (p: Partial<RenderItem>): RenderItem => ({ rel: "studio/renders/a.mp4", abs: "/w/studio/renders/a.mp4", name: "a.mp4", duration: 12.5,
  width: 1280, height: 720, created_at: "2026-10-18T10:00:00Z", missing: 0, clips: 3, ...p })
const job = (p: Partial<Job>): Job => ({ id: "j", kind: "render", target: "render:x", scene_id: "", status: "running", error: null,
  result: null, created_at: "x", finished_at: null, progress: { total: 100, done: 40, failed: 0, current: "" }, ...p })
const base = { aspect: "16:9", busy: false, onRender: noop, onCut: noop }

describe("4d – Ausgabe: Übersicht", () => {
  it("Länge, Clips, Platzhalter; Größe aus dem Format", () => {
    expect(deliverSummary([c("video", 0, 4), c("image", 5, 3), c("placeholder", 8, 2), c("placeholder", 10, 1, true)]))
      .toEqual({ seconds: 11, clips: 4, placeholders: 2, missing: 1 })
    expect(deliverSummary([])).toEqual({ seconds: 0, clips: 0, placeholders: 0, missing: 0 })
    expect(filmSize("9:16")).toEqual([720, 1280])
    expect(filmSize("21:9")).toEqual([1680, 720])
    expect(filmSize("kaputt")).toEqual([1280, 720])
    expect(minutes(75.4)).toBe("1:15")
    expect(minutes(9)).toBe("0:09")
    expect(minutes(12.5)).toBe("0:12")
    expect(minutes(59.9)).toBe("0:59")
    expect(minutes(60 - 1e-9)).toBe("1:00")                                         // Gleitkomma-Rest zählt als 1:00
  })
})

describe("4d – Ausgabe: Reiter", () => {
  it("leere Zeitleiste: Hinweis und Knopf „Zum Schneiden“, „Film als MP4 erzeugen“ gesperrt", () => {
    const out = html(<DeliverPanel clips={[]} renders={[]} job={null} {...base} />)
    expect(out).toContain("deliver_empty")
    expect(buttons(out)).toContain("soon_to_cut")
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*data-deliver-run/)
  })

  it("mit Clips: Übersicht, Hinweis bei Platzhaltern, Knopf frei", () => {
    const out = html(<DeliverPanel clips={[c("video", 0, 4), c("placeholder", 4, 2)]} renders={[]} job={null} {...base} aspect="9:16" />)
    expect(out).toContain('deliver_summary:{"length":"0:06","clips":2,"width":720,"height":1280}')
    expect(out).toContain('deliver_placeholders:{"count":1}')
    expect(buttons(out)).toContain("deliver_run")
    expect(out).not.toMatch(/<button[^>]*disabled=""[^>]*data-deliver-run/)
    expect(out).toContain("deliver_none")
    expect(html(<DeliverPanel clips={[c("video", 0, 4)]} renders={[]} job={null} {...base} />)).not.toContain("deliver_placeholders")
  })

  it("läuft: Fortschritt in Prozent, Knopf gesperrt; fehlgeschlagen: Meldung", () => {
    const run = html(<DeliverPanel clips={[c("video", 0, 4)]} renders={[]} job={job({})} {...base} />)
    expect(run).toContain('deliver_running:{"percent":40}')
    expect(run).toMatch(/<button[^>]*disabled=""[^>]*data-deliver-run/)
    const failed = html(<DeliverPanel clips={[c("video", 0, 4)]} renders={[]} job={job({ status: "failed", error: "render_failed" })} {...base} />)
    expect(failed).toContain("job_err.render_failed")
  })

  it("fertige Filme: neueste oben, Abspieler, „Herunterladen“ als Link mit download, Hinweis bei fehlenden Medien", () => {
    const out = html(<DeliverPanel clips={[c("video", 0, 4)]} renders={[R({}), R({ rel: "studio/renders/b.mp4", abs: "/w/b.mp4", name: "b.mp4", missing: 2 })]}
      job={null} {...base} />)
    expect((out.match(/data-deliver-film=/g) || []).length).toBe(2)
    expect(out).toContain('<video')
    expect(out).toMatch(/<a[^>]*href="\/f\/w\/studio\/renders\/a.mp4"[^>]*download="[^"]+\.mp4"/)
    expect(out).toContain("deliver_download")
    expect(out).toContain('deliver_missing:{"count":2}')
    expect(out).toContain('deliver_film_info:{"length":"0:12","width":1280,"height":720}')
  })
})
