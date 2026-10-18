import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { HearDialog } from "./HearDialog"
import { costText, finishedHear, type HearInfo } from "./hearLogic"
import { jobText } from "./jobLogic"
import { SubtitleList } from "./SubtitleList"
import type { Job } from "./planApi"

const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const noop = () => {}
const INFO: HearInfo = { seconds: 95, model: "openai/whisper-large-v3", cloud: true, existing: 0, max_seconds: 3600 }
const job = (p: Partial<Job>): Job => ({ id: "j1", kind: "transcribe", target: "subtitles:p:de", scene_id: "", status: "done", error: null,
  result: { count: 4 }, created_at: "x", finished_at: "y", ...p })

describe("6b – heraushören (rein)", () => {
  it("Kosten nach Filmlänge: unter 1 Cent, sonst etwa N Cent (≈ 0,05 ct je Minute, aufgerundet)", () => {
    expect(costText(95)).toEqual({ key: "hear_cost_below" })
    expect(costText(3600)).toEqual({ key: "hear_cost_about", cents: 3 })
    expect(costText(2000)).toEqual({ key: "hear_cost_about", cents: 2 })
    expect(costText(1340)).toEqual({ key: "hear_cost_about", cents: 2 })            // 1,005 ct → aufgerundet
    expect(costText(1320)).toEqual({ key: "hear_cost_below" })                       // 0,99 ct
  })
  it("fertig: nur der in diesem Fenster gestartete Auftrag", () => {
    const pending = new Set(["j1"])
    expect(finishedHear([job({ status: "running" })], pending)).toBeNull()
    expect(finishedHear([job({})], pending)?.id).toBe("j1")
    expect(finishedHear([job({ id: "j9" })], pending)).toBeNull()
    expect(finishedHear([job({ kind: "speech" })], pending)).toBeNull()
    expect(finishedHear([job({ status: "failed", error: "no_key" })], pending)?.status).toBe("failed")
  })
  it("Fehlertexte für das Heraushören", () => {
    const t = (k: string) => k
    for (const e of ["no_key", "provider_rejected", "empty_answer", "no_speech_found", "changed", "render_failed"])
      expect(jobText(t, job({ status: "failed", error: e }))).toBe(`job_err.${e}_hear`)
    expect(jobText(t, job({ status: "failed", error: "provider_unreachable" }))).toBe("job_err.provider_unreachable")
  })
})

describe("6b – Dialog „Aus dem Ton heraushören“", () => {
  const dlg = (p: Partial<React.ComponentProps<typeof HearDialog>> = {}) =>
    html(<HearDialog info={INFO} language="de" job={null} busy={false} onRun={noop} onClose={noop} {...p} />)
  it("Sprache, Länge, Modell, Kosten, Hinweis „ohne Musik“, Starten", () => {
    const out = dlg()
    expect(out).toContain("lang.de")
    expect(out).toContain("1:35")
    expect(out).toContain("openai/whisper-large-v3")
    expect(out).toContain("hear_cost_below")
    expect(out).toContain("hear_no_music")
    expect(out.match(/<button[^>]*data-hear-run[^>]*>/)?.[0]).not.toContain('disabled=""')
    expect(out).not.toContain("hear_replaces")
  })
  it("vorhandene Untertitel: Hinweis aufs Ersetzen; läuft: gesperrt mit Hinweis; Fehler mit Text", () => {
    expect(dlg({ info: { ...INFO, existing: 3 } })).toContain('hear_replaces:{"count":3}')
    const run = dlg({ job: job({ status: "running", result: null }) })
    expect(run.match(/<button[^>]*data-hear-run[^>]*>/)?.[0]).toContain('disabled=""')
    expect(run).toContain("hear_running")
    expect(dlg({ job: job({ status: "failed", error: "no_speech_found" }) })).toContain("job_err.no_speech_found_hear")
  })
  it("lokales Modell, zu lang, nichts zu hören: Hinweis statt Start", () => {
    for (const [p, k] of [[{ cloud: false }, "hear_needs_cloud"], [{ seconds: 4000 }, "hear_too_long"], [{ seconds: 0 }, "hear_nothing"]] as const) {
      const out = dlg({ info: { ...INFO, ...p } })
      expect(out, k).toContain(k)
      expect(out.match(/<button[^>]*data-hear-run[^>]*>/)?.[0], k).toContain('disabled=""')
    }
  })
  it("lädt: Hinweis", () => {
    expect(html(<HearDialog info={null} language="de" job={null} busy={false} onRun={noop} onClose={noop} />)).toContain("loading")
  })
})

describe("6b – Liste: Knopf und gesperrt während des Heraushörens", () => {
  const list = (p: Partial<React.ComponentProps<typeof SubtitleList>> = {}) => html(
    <SubtitleList cues={[{ id: "a", start: 0, end: 2, text: "Eins" }]} selected="a" time={1} hasSpeech busy={false} save="saved" canUndo canRedo={false}
      onSelect={noop} onChange={noop} onAction={noop} onFromSpeech={noop} onExport={noop} onHear={noop} hearing={false} {...p} />)
  it("Knopf „Aus dem Ton heraushören …“", () => {
    expect(list()).toMatch(/<button[^>]*data-sub-hear[^>]*>.*hear_open/)
  })
  it("während des Heraushörens: Bearbeiten gesperrt, Hinweis", () => {
    const out = list({ hearing: true })
    expect(out).toContain("hear_running")
    expect(out.match(/<textarea[^>]*data-sub-text="a"[^>]*>/)?.[0]).toContain('readOnly=""')
    for (const k of ["split", "delete"]) expect(out.match(new RegExp(`<button[^>]*data-sub-action="${k}"[^>]*>`))?.[0], k).toContain('disabled=""')
    expect(out.match(/<button[^>]*data-sub-from-speech[^>]*>/)?.[0]).toContain('disabled=""')
    expect(out.match(/<button[^>]*data-sub-hear[^>]*>/)?.[0]).toContain('disabled=""')
  })
})
