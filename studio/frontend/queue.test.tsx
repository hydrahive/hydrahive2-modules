import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})) } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import { DeliverPanel } from "./DeliverPanel"
import { RenderQueue } from "./RenderQueue"
import { studioI18n } from "./i18n"
import type { Job } from "./planApi"
import { QUEUE_MAX, queueFull, queueJobs, startedNotice } from "./queueLogic"
import type { TimelineClip } from "./timelineApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const clip: TimelineClip = { id: "c", kind: "video", start: 0, in: 0, out: 4, media_rel: "x", scene_id: "", shot_id: "", label: "l" }
let n = 0
const job = (p: Partial<Job> & { info?: Record<string, unknown> }): Job => ({ id: `j${++n}`, kind: "render", target: "render:x", scene_id: "", status: "queued",
  error: null, result: null, created_at: `2026-10-19T01:0${n % 10}:00.000000Z`, finished_at: null,
  progress: { total: 100, done: 0, failed: 0, current: "" }, info: { aspect: "9:16", quality: "preview", subtitles: false }, ...p } as Job)
const base = { clips: [clip], renders: [], busy: false, onRender: noop, onCut: noop, aspect: "16:9" }

describe("7c – Warteschlange: Logik", () => {
  it("nur Filme, älteste oben, höchstens 6; laufende und wartende zählen gegen die 5", () => {
    const list = [job({ status: "done", created_at: "2026-10-19T01:05:00Z" }), job({ kind: "image", status: "running" }),
      job({ status: "running", created_at: "2026-10-19T01:06:00Z" }), job({ status: "queued", created_at: "2026-10-19T01:07:00Z" })]
    expect(queueJobs(list).map((j) => j.created_at)).toEqual(["2026-10-19T01:05:00Z", "2026-10-19T01:06:00Z", "2026-10-19T01:07:00Z"])
    const many = Array.from({ length: 9 }, (_, i) => job({ status: "done", created_at: `2026-10-19T02:0${i}:00Z` }))
    expect(queueJobs(many).map((j) => j.created_at.slice(14, 16))).toEqual(["03", "04", "05", "06", "07", "08"])   // die neuesten 6
    expect(QUEUE_MAX).toBe(5)
    expect(queueFull(Array.from({ length: 5 }, () => job({ status: "queued" })))).toBe(true)
    expect(queueFull([...Array.from({ length: 4 }, () => job({ status: "queued" })), job({ status: "done" }), job({ status: "failed" })])).toBe(false)
    expect(queueFull([...Array.from({ length: 4 }, () => job({ status: "queued" })), job({ status: "running" })])).toBe(true)
  })

  it("Meldung nach dem Klick: läuft sofort oder Platz in der Warteschlange", () => {
    const t = (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k)
    expect(startedNotice(t, { status: "running", position: 1 })).toBe("notice_render_started")
    expect(startedNotice(t, { status: "queued", position: 3 })).toBe('notice_render_queued:{"position":3}')
    expect(startedNotice(t, {})).toBe("notice_render_started")
  })
})

describe("7c – Warteschlange: Liste", () => {
  it("jeder Film mit Vorlage und Zustand; Abbrechen nur bei wartend/laufend", () => {
    const out = html(<RenderQueue jobs={[job({ status: "done", info: { aspect: "16:9", quality: "high", subtitles: true } }),
      job({ status: "running", progress: { total: 100, done: 40, failed: 0, current: "" } }), job({ status: "queued" }),
      job({ status: "failed", error: "render_failed" }), job({ status: "cancelled" })]} cancelling={null} onCancel={noop} />)
    expect(out).toContain("queue_title")
    expect(out).toContain('deliver_film_preset:{"aspect":"16:9","quality":"deliver_quality.high"}')
    expect(out).toContain("queue_subtitles")
    expect(out).toContain("queue_status.done")
    expect(out).toContain('queue_status.running:{"percent":40}')
    expect(out).toContain("queue_status.queued")
    expect(out).toContain("job_err.render_failed")
    expect(out).toContain("queue_status.cancelled")
    expect((out.match(/data-queue-cancel/g) || []).length).toBe(2)
    expect((out.match(/data-queue-item/g) || []).length).toBe(5)
  })

  it("Abbrechen ruft den richtigen Auftrag; während des Abbrechens gesperrt", () => {
    const onCancel = vi.fn()
    const q = job({ id: "wartet", status: "queued" })
    const tree = RenderQueue({ jobs: [q], cancelling: null, onCancel }) as React.ReactElement
    const find = (node: unknown): { props: Record<string, unknown> } | null => {
      if (!node || typeof node !== "object") return null
      if (Array.isArray(node)) { for (const x of node) { const f = find(x); if (f) return f } return null }
      const el = node as { props?: Record<string, unknown> }
      if (el.props?.["data-queue-cancel"]) return el as { props: Record<string, unknown> }
      return find(el.props?.children)
    }
    ;(find(tree)!.props.onClick as () => void)()
    expect(onCancel).toHaveBeenCalledWith("wartet")
    expect(html(<RenderQueue jobs={[q]} cancelling="wartet" onCancel={noop} />)).toMatch(/<button[^>]*disabled=""[^>]*data-queue-cancel/)
  })

  it("leer: keine Liste", () => {
    expect(html(<RenderQueue jobs={[]} cancelling={null} onCancel={noop} />)).toBe("")
  })
})

describe("7c – Reiter „Ausgabe“", () => {
  it("während ein Film läuft: Knopf und Auswahl frei (nächste Fassung anstoßen), Liste sichtbar", () => {
    const out = html(<DeliverPanel {...base} job={null} queue={[job({ status: "running" }), job({ status: "queued" })]} cancelling={null} onCancel={noop} />)
    expect(out).not.toMatch(/<button[^>]*disabled=""[^>]*data-deliver-run/)
    expect(out).not.toMatch(/<select[^>]*disabled=""/)
    expect(out).toContain("queue_title")
  })

  it("Schlange voll: Knopf gesperrt mit Hinweis", () => {
    const out = html(<DeliverPanel {...base} job={null} queue={Array.from({ length: 5 }, () => job({ status: "queued" }))} cancelling={null} onCancel={noop} />)
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*data-deliver-run/)
    expect(out).toContain('queue_full:{"max":5}')
  })
})

describe("7c – Texte", () => {
  it("de/en vorhanden, auch der Fehler studio_render_queue_full", () => {
    for (const lang of ["de", "en"] as const) {
      const s = studioI18n[lang].studio as unknown as Record<string, unknown> & { queue_status: Record<string, string>; err: Record<string, string> }
      for (const k of ["queue_title", "queue_cancel", "queue_cancelling", "queue_full", "queue_subtitles", "notice_render_queued"]) expect(s[k], `${lang} ${k}`).toBeTruthy()
      for (const st of ["queued", "running", "done", "cancelled"]) expect(s.queue_status[st], `${lang} ${st}`).toBeTruthy()
      expect(s.err.studio_render_queue_full).toBeTruthy()
    }
  })
})
