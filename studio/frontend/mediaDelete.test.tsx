import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
const del = vi.fn((..._a: unknown[]) => Promise.resolve({ deleted: "x" }))
const get = vi.fn((..._a: unknown[]) => new Promise(() => {}))
vi.mock("@/shared/api-client", () => ({ api: { get: (...a: unknown[]) => get(...a), post: vi.fn(), delete: (...a: unknown[]) => del(...a) } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import type { LibraryItem } from "./api"
import { FreeGallery } from "./FreeGallery"
import { MediaActions } from "./MediaActions"
import { MediaDeleteDialog } from "./MediaDeleteDialog"
import { mediaApi, downloadName as mediaDownloadName, usageLines } from "./mediaLogic"
import { studioI18n } from "./i18n"
import type { Shot } from "./planApi"
import { ShotImage } from "./ShotImage"
import { ShotVideo } from "./ShotVideo"
import { DeliverPanel } from "./DeliverPanel"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const item = (p: Partial<LibraryItem> = {}): LibraryItem => ({ id: "i", kind: "image", origin: "ai", source: "studio", name: "Hafen", rel: "studio/media/images/a.png",
  abs: "/w/studio/media/images/a.png", size: 10, created_at: "2026-10-19T08:00:00Z", deletable: true, ...p })
const shot = (p: Partial<Shot> = {}): Shot => ({ id: "s", shot: "wide", prompt: "x", element_ids: [], duration: 5, status: "image_ready",
  image_rel: "studio/media/images/a.png", video_rel: null, variants: ["studio/media/images/a.png", "studio/media/images/b.png"], ...p } as Shot)

describe("C1 – Logik", () => {
  it("Rückfrage nennt, wo die Datei benutzt wird", () => {
    expect(usageLines({ own: true, shots: [{ scene_id: "a", shot_id: "b", label: "Hafen · Shot 1" }, { scene_id: "a", shot_id: "c", label: "Hafen · Shot 2" }],
      clips: 2, elements: [{ id: "e", name: "Hydra" }] })).toEqual([
      { key: "media_used_shots", o: { count: 2, names: "Hafen · Shot 1, Hafen · Shot 2" } },
      { key: "media_used_clips", o: { count: 2 } },
      { key: "media_used_elements", o: { count: 1, names: "Hydra" } },
    ])
    expect(usageLines({ own: true, shots: [], clips: 0, elements: [] })).toEqual([])
  })

  it("Dateiname beim Herunterladen: lesbarer Name + Endung", () => {
    expect(mediaDownloadName(item({ name: "Hafen am Abend" }))).toBe("Hafen am Abend.png")
    expect(mediaDownloadName(item({ name: "a/b:c", rel: "studio/media/voice/x.mp3" }))).toBe("a-b-c.mp3")
    expect(mediaDownloadName(item({ name: "", rel: "studio/media/free/q.webp" }))).toBe("q.webp")
  })

  it("API: Verwendung + Löschen mit rel als Parameter", () => {
    void mediaApi.usage("p1", "studio/media/images/a b.png")
    expect(get).toHaveBeenLastCalledWith("/modules/studio/projects/p1/media/usage?rel=studio%2Fmedia%2Fimages%2Fa%20b.png")
    void mediaApi.remove("p1", "studio/renders/x.mp4")
    expect(del).toHaveBeenLastCalledWith("/modules/studio/projects/p1/media?rel=studio%2Frenders%2Fx.mp4")
  })
})

describe("C1 – Bibliothek: Herunterladen und Löschen am gewählten Medium", () => {
  it("eigene Datei: Link „Herunterladen“ mit Dateinamen + Knopf „Löschen …“", () => {
    const out = html(<MediaActions item={item()} onDelete={noop} />)
    expect(out).toMatch(/<a[^>]*href="\/f\/w\/studio\/media\/images\/a.png"[^>]*download="Hafen.png"[^>]*>.*media_download/s)
    expect(out).toMatch(/<button[^>]*data-media-delete[^>]*>.*media_delete/s)
  })

  it("fremde Datei (Atelier …): Herunterladen ja, Löschen nein, Hinweis wo man löscht", () => {
    const out = html(<MediaActions item={item({ source: "atelier", deletable: false, rel: "atelier/images/x.png" })} onDelete={noop} />)
    expect(out).toContain("media_download")
    expect(out).not.toContain("data-media-delete")
    expect(out).toContain('media_not_own:{"source":"source.atelier"}')
  })

  it("Figuren (Bausteine aus dem Atelier) haben keine Datei zum Herunterladen", () => {
    expect(html(<MediaActions item={item({ kind: "element", source: "atelier", deletable: false })} onDelete={noop} />)).not.toContain("media_download")
  })
})

describe("C1 – Rückfrage vor dem Löschen", () => {
  it("lädt: Hinweis; danach Verwendung + rote Schaltfläche; nichts benutzt: eigener Satz", () => {
    expect(html(<MediaDeleteDialog name="Hafen" usage={null} busy={false} onConfirm={noop} onClose={noop} />)).toContain("media_usage_loading")
    const used = html(<MediaDeleteDialog name="Hafen" busy={false} onConfirm={noop} onClose={noop}
      usage={{ own: true, shots: [{ scene_id: "a", shot_id: "b", label: "Hafen · Shot 1" }], clips: 1, elements: [] }} />)
    expect(used).toContain('media_delete_question:{"name":"Hafen"}')
    expect(used).toContain('media_used_shots:{"count":1,"names":"Hafen · Shot 1"}')
    expect(used).toContain('media_used_clips:{"count":1}')
    expect(used).toContain("media_delete_after")
    expect(used).toMatch(/<button[^>]*data-media-delete-confirm/)
    const unused = html(<MediaDeleteDialog name="Hafen" busy={false} onConfirm={noop} onClose={noop} usage={{ own: true, shots: [], clips: 0, elements: [] }} />)
    expect(unused).toContain("media_unused")
    expect(unused).not.toContain("media_delete_after")
  })

  it("während des Ladens der Verwendung ist Löschen gesperrt", () => {
    expect(html(<MediaDeleteDialog name="x" usage={null} busy={false} onConfirm={noop} onClose={noop} />)).toMatch(/<button[^>]*disabled=""[^>]*data-media-delete-confirm/)
  })
})

describe("C1 – Löschen am Shot, bei freien Bildern und fertigen Filmen", () => {
  it("jede Bildvariante hat ein „Bild löschen“-Kreuz; ohne onDelete keins", () => {
    const onDelete = vi.fn()
    const out = html(<ShotImage shot={shot()} base="/w" job={null} onGenerate={noop} onChoose={noop} onDelete={onDelete} />)
    expect((out.match(/data-shot-variant-delete=/g) || []).length).toBe(2)
    expect(out).toContain('aria-label="image_delete"')
    expect(html(<ShotImage shot={shot()} base="/w" job={null} onGenerate={noop} onChoose={noop} />)).not.toContain("data-shot-variant-delete")
  })

  it("Video am Shot: „Video löschen …“", () => {
    expect(html(<ShotVideo shot={shot({ video_rel: "studio/media/videos/v.mp4" })} base="/w" job={null} onGenerate={noop} onDelete={noop} />)).toMatch(/data-shot-video-delete[^>]*>.*video_delete/s)
    expect(html(<ShotVideo shot={shot()} base="/w" job={null} onGenerate={noop} onDelete={noop} />)).not.toContain("data-shot-video-delete")
  })

  it("freies Bild: „Löschen …“", () => {
    const free = item({ source: "studio_free", rel: "studio/media/free/f.png" })
    expect(html(<FreeGallery items={[free]} plan={null} busy={false} onAssign={noop} onTimeline={noop} onDelete={noop} />)).toMatch(/data-free-delete="studio\/media\/free\/f.png"/)
  })

  it("fertiger Film: „Löschen …“ neben „Herunterladen“", () => {
    const out = html(<DeliverPanel clips={[]} aspect="16:9" busy={false} onRender={noop} onCut={noop} onDeleteFilm={noop}
      renders={[{ rel: "studio/renders/a.mp4", abs: "/w/a.mp4", name: "a.mp4", duration: 3, width: 1280, height: 720, created_at: "2026-10-19T08:00:00Z", missing: 0, clips: 1 }]} />)
    expect(out).toMatch(/data-deliver-delete="studio\/renders\/a.mp4"/)
  })
})

describe("C1 – Texte", () => {
  it("de/en vorhanden", () => {
    for (const lang of ["de", "en"] as const) {
      const s = studioI18n[lang].studio as unknown as Record<string, unknown> & { err: Record<string, string> }
      for (const k of ["media_download", "media_delete", "media_delete_question", "media_used_shots_one", "media_used_shots_other",
        "media_used_clips_one", "media_used_clips_other", "media_used_elements_one", "media_used_elements_other", "media_delete_after", "media_unused",
        "media_usage_loading", "media_not_own", "media_deleted", "image_delete", "video_delete"]) expect(s[k], `${lang} ${k}`).toBeTruthy()
      for (const c of ["studio_media_busy", "studio_media_not_own", "studio_media_not_found"]) expect(s.err[c], `${lang} ${c}`).toBeTruthy()
    }
  })
})
