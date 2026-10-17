import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { CutInspector } from "./CutInspector"
import { CutTimeline } from "./CutTimeline"
import { FromPlanDialog } from "./FromPlanDialog"
import { activeAt, clipLength, filmLength, followView, nextMediaClip, sourceTime } from "./cutLogic"
import type { Timeline, TimelineClip } from "./timelineApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const attr = (out: string, name: string) => [...out.matchAll(new RegExp(`${name}="([^"]+)"`, "g"))].map((m) => m[1])
const clip = (p: Partial<TimelineClip>): TimelineClip => ({ id: "c", kind: "image", start: 0, in: 0, out: 5, media_rel: "studio/media/images/a.png",
  scene_id: "", shot_id: "", label: "x", ...p })
const CLIPS = [
  clip({ id: "v1", kind: "video", start: 0, in: 1, out: 5, media_rel: "studio/media/videos/a.mp4", label: "Hafen · Shot 1", shot_id: "s1", scene_id: "sc" }),
  clip({ id: "i1", kind: "image", start: 4, out: 3, label: "Hafen · Shot 2" }),
  clip({ id: "p1", kind: "placeholder", start: 9, out: 2, media_rel: "", label: "Hafen · Shot 3", shot_id: "s3", scene_id: "sc" }),
  clip({ id: "v2", kind: "video", start: 11, in: 0, out: 4, media_rel: "studio/media/videos/b.mp4", label: "Sturm" }),
]
const TL: Timeline = { revision: 3, fps: 25, tracks: [{ id: "V1", kind: "video", clips: CLIPS }] }

describe("Studio 4a – Abspiel-Logik", () => {
  it("Länge je Clip und des Films (Lücke bei 7–9 zählt mit)", () => {
    expect(clipLength(CLIPS[0])).toBe(4)
    expect(filmLength(CLIPS)).toBe(15)
    expect(filmLength([])).toBe(0)
  })

  it("welcher Clip bei t: Start inklusive, Ende exklusiv, Lücke = null", () => {
    expect(activeAt(CLIPS, 0)?.id).toBe("v1")
    expect(activeAt(CLIPS, 3.99)?.id).toBe("v1")
    expect(activeAt(CLIPS, 4)?.id).toBe("i1")
    expect(activeAt(CLIPS, 7.5)).toBeNull()
    expect(activeAt(CLIPS, 9)?.id).toBe("p1")
    expect(activeAt(CLIPS, 15)).toBeNull()
    expect(activeAt(CLIPS, -1)).toBeNull()
    expect(activeAt([...CLIPS].reverse(), 4)?.id).toBe("i1")           // Reihenfolge im Array egal
  })

  it("Zeit im Medium = in + (t − start)", () => {
    expect(sourceTime(CLIPS[0], 0)).toBe(1)
    expect(sourceTime(CLIPS[0], 2.5)).toBe(3.5)
    expect(sourceTime(CLIPS[3], 12)).toBe(1)
  })

  it("Ausschnitt passt sich der Filmlänge an und folgt dem Abspielkopf", () => {
    expect(followView({ start: 0, span: 30 }, 2, 15)).toEqual({ start: 0, span: 15 })     // ganzer Film passt hinein
    expect(followView({ start: 0, span: 10 }, 5, 60)).toEqual({ start: 0, span: 10 })     // Kopf sichtbar → bleibt
    expect(followView({ start: 0, span: 10 }, 30, 60)).toEqual({ start: 28, span: 10 })   // Kopf draußen → folgt
    expect(followView({ start: 50, span: 10 }, 0, 0)).toEqual({ start: 0, span: 1 })      // leerer Film, keine Division durch 0
  })

  it("nächster Videoclip zum Vorladen (Bilder/Platzhalter übersprungen)", () => {
    expect(nextMediaClip(CLIPS, 0)?.id).toBe("v2")
    expect(nextMediaClip(CLIPS, 5)?.id).toBe("v2")
    expect(nextMediaClip(CLIPS, 11)).toBeNull()
    const later = clip({ id: "v3", kind: "video", start: 30, out: 2, media_rel: "studio/media/videos/c.mp4" })
    expect(nextMediaClip([later, ...CLIPS], 5)?.id).toBe("v2")          // der nächste nach Zeit, nicht der erste im Array
    expect(nextMediaClip([...CLIPS, later], 5)?.id).toBe("v2")          // … und auch nicht der letzte
  })
})

describe("Studio 4a – Oberfläche", () => {
  it("Zeitleiste: echte Clips mit Lage, Platzhalter markiert, kein Beispiel-Hinweis", () => {
    const out = html(<CutTimeline timeline={TL} base="/w/p" time={2} view={{ start: 0, span: 15 }} selected="v1"
      onView={noop} onSeek={noop} onSelect={noop} onFromPlan={noop} busy={false} />)
    expect(attr(out, "data-cut-clip")).toEqual(["v1", "i1", "p1", "v2"])
    expect(out).toMatch(/data-cut-clip="p1"[^>]*data-placeholder="1"/)
    expect(out).toMatch(/data-cut-clip="i1"[^>]*style="left:26\.6\d*%;width:20%"/)
    expect(out).not.toContain("data-studio-demo-badge")
    expect(out).toContain("data-studio-overview")
    expect(out).toContain('data-cut-length="15"')
    expect(out).toContain("data-cut-from-plan")                     // Übernehmen geht auch bei gefüllter Fassung
  })

  it("Zeitleiste leer: Hinweis mit Knopf „Aus dem Drehbuch übernehmen“", () => {
    const out = html(<CutTimeline timeline={{ ...TL, tracks: [{ id: "V1", kind: "video", clips: [] }] }} base="/w/p" time={0}
      view={{ start: 0, span: 10 }} selected={null} onView={noop} onSeek={noop} onSelect={noop} onFromPlan={noop} busy={false} />)
    expect(out).toContain("cut_empty")
    expect(out).toContain("data-cut-from-plan")
    expect(attr(out, "data-cut-clip")).toEqual([])
  })

  it("Eigenschaften: Angaben zum Clip; Platzhalter mit Sprung ins Planen; fehlendes Medium", () => {
    const v = html(<CutInspector clip={CLIPS[0]} onPlan={noop} />)
    expect(v).toContain("Hafen · Shot 1")
    expect(v).toContain("cut_kind.video")
    expect(v).toContain('data-cut-start="0"')
    expect(v).toContain('data-cut-len="4"')
    expect(v).not.toContain("data-cut-to-plan")
    const p = html(<CutInspector clip={CLIPS[2]} onPlan={noop} />)
    expect(p).toContain("data-cut-to-plan")
    expect(p).not.toContain("cut_missing")
    expect(html(<CutInspector clip={{ ...CLIPS[2], missing: true }} onPlan={noop} />)).toContain("cut_missing")
    expect(html(<CutInspector clip={{ ...CLIPS[2], shot_id: "" }} onPlan={noop} />)).not.toContain("data-cut-to-plan")   // ohne Shot kein Sprung
    expect(html(<CutInspector clip={null} onPlan={noop} />)).toContain("nothing_selected")
  })

  it("Dialog „Ersetzen?“ ohne Browser-Popup", () => {
    const out = html(<FromPlanDialog count={4} busy={false} onConfirm={noop} onClose={noop} />)
    expect(out).toContain('role="dialog"')
    expect(out).toContain('cut_replace_question:{"count":4}')
    expect(out).toContain("data-cut-replace")
    expect(html(<FromPlanDialog count={4} busy onConfirm={noop} onClose={noop} />).match(/<button[^>]*data-cut-replace[^>]*>/)?.[0]).toContain(' disabled=""')
  })
})
