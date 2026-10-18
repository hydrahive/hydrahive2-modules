import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o && !("defaultValue" in o) ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { BatchDialog } from "./BatchDialog"
import { BatchMenu } from "./BatchMenu"
import { BatchStatus } from "./BatchStatus"
import { activeBatch, isBatch } from "./jobLogic"
import type { Job } from "./planApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const job = (p: Partial<Job>): Job => ({ id: "j", kind: "images_all", target: "batch:p", scene_id: "", status: "running", error: null, result: null,
  created_at: "2026-10-17T10:00:00.000001Z", finished_at: null, progress: { total: 8, done: 3, failed: 1, current: "Hafen · Shot 4" }, ...p })

describe("Studio 3c – Sammelaufträge", () => {
  it("Logik: Sammelauftrag erkennen, laufenden finden", () => {
    expect(isBatch(job({}))).toBe(true)
    expect(isBatch(job({ kind: "image", progress: undefined }))).toBe(false)
    expect(activeBatch([job({ id: "a", status: "done" }), job({ id: "b" })])?.id).toBe("b")
    expect(activeBatch([job({ status: "cancelled" })])).toBeNull()
  })

  it("Menü: vier Punkte (seit 5c auch Sprache), gesperrt während ein Sammelauftrag läuft", () => {
    const out = html(<BatchMenu running={false} onPick={noop} />)
    expect([...out.matchAll(/data-batch-pick="([^"]+)"/g)].map((m) => m[1])).toEqual(["decompose_all", "images_all", "videos_all", "speech_all"])
    expect(html(<BatchMenu running onPick={noop} />).match(/<button[^>]*data-batch-open[^>]*>/)?.[0]).toContain(' disabled=""')
  })

  it("Dialog: Anzahl und Modell, eigener Knopf; bei 0 nur ein Hinweis", () => {
    const out = html(<BatchDialog kind="images_all" preview={{ count: 5, model: "black-forest-labs/flux.2-klein-4b" }} busy={false} onRun={noop} onClose={noop} />)
    expect(out).toContain('batch_question.images_all:{"count":5,"model":"black-forest-labs/flux.2-klein-4b"}')
    expect(out).toContain("batch_hint")
    expect(out).toContain("data-batch-run")
    expect(out).toContain('role="dialog"')
    const none = html(<BatchDialog kind="videos_all" preview={{ count: 0, model: "x" }} busy={false} onRun={noop} onClose={noop} />)
    expect(none).toContain("batch_nothing.videos_all")
    expect(none).not.toContain("data-batch-run")
    expect(html(<BatchDialog kind="images_all" preview={null} busy={false} onRun={noop} onClose={noop} />)).toContain("loading")
  })

  it("Kopfzeile: Fortschritt „3 von 8“, aktueller Schritt, Fehlschläge, Abbrechen", () => {
    const out = html(<BatchStatus job={job({})} cancelling={false} onCancel={noop} />)
    expect(out).toContain('batch_progress.images_all:{"done":3,"total":8}')
    expect(out).toContain("Hafen · Shot 4")
    expect(out).toContain('batch_failed:{"count":1}')
    expect(out).toContain("data-batch-cancel")
    const c = html(<BatchStatus job={job({})} cancelling onCancel={noop} />)
    expect(c.match(/<button[^>]*data-batch-cancel[^>]*>/)?.[0]).toContain(' disabled=""')
    expect(c).toContain("batch_cancelling")
    expect(html(<BatchStatus job={job({ progress: { total: 2, done: 0, failed: 0, current: "" } })} cancelling={false} onCancel={noop} />)).not.toContain("batch_failed")
  })
})
