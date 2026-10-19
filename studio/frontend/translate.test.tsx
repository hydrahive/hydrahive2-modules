import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(() => new Promise(() => {})) } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import { DeliverPanel } from "./DeliverPanel"
import { jobText } from "./jobLogic"
import type { Job } from "./planApi"
import type { RenderItem } from "./renderApi"
import { SubtitleLanguagePick } from "./SubtitleLanguagePick"
import { TranslateDialog } from "./TranslateDialog"
import { finishedTranslate, languageChoices, targetChoices, type LanguageList } from "./translateLogic"

const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const noop = () => {}
const LIST: LanguageList = { film: "de", languages: [{ language: "de", count: 3 }, { language: "en", count: 3 }] }
const job = (p: Partial<Job>): Job => ({ id: "j1", kind: "translate", target: "subtitles:p:fr", scene_id: "", status: "done", error: null,
  result: { count: 3 }, created_at: "x", finished_at: "y", ...p })

describe("6c – Sprachen (rein)", () => {
  it("Auswahl: Filmsprache zuerst, dann vorhandene; eine gerade gewählte neue Sprache bleibt sichtbar", () => {
    expect(languageChoices(LIST, "de")).toEqual([{ language: "de", count: 3, film: true }, { language: "en", count: 3, film: false }])
    expect(languageChoices(LIST, "fr").map((x) => x.language)).toEqual(["de", "en", "fr"])
    expect(languageChoices(null, "de")).toEqual([{ language: "de", count: 0, film: true }])
  })
  it("Ziele: alle Sprachen außer der Ausgangssprache; vorhandene mit Anzahl", () => {
    const out = targetChoices(LIST, "de")
    expect(out.length).toBe(17)
    expect(out.find((x) => x.language === "de")).toBeUndefined()
    expect(out.find((x) => x.language === "en")?.count).toBe(3)
    expect(out.find((x) => x.language === "fr")?.count).toBe(0)
  })
  it("fertiger Auftrag: nur der eigene", () => {
    const pending = new Set(["j1"])
    expect(finishedTranslate([job({ status: "running" })], pending)).toBeNull()
    expect(finishedTranslate([job({})], pending)?.id).toBe("j1")
    expect(finishedTranslate([job({ kind: "transcribe" })], pending)).toBeNull()
    expect(finishedTranslate([job({ id: "x" })], pending)).toBeNull()
    expect(finishedTranslate([job({ status: "failed", error: "bad_answer" })], pending)?.status).toBe("failed")
  })
  it("Fehlertexte", () => {
    const t = (k: string) => k
    for (const e of ["provider_failed", "bad_answer", "changed"]) expect(jobText(t, job({ status: "failed", error: e }))).toBe(`job_err.${e}_translate`)
  })
})

describe("6c – Auswahl der Sprache im Reiter", () => {
  it("Liste mit Original-Kennzeichen, gewählte Sprache, Knopf „Übersetzen …“", () => {
    const out = html(<SubtitleLanguagePick list={LIST} value="en" busy={false} onChange={noop} onTranslate={noop} />)
    expect(out).toMatch(/<option value="de"[^>]*>sub_lang_film:\{"name":"lang.de"\}/)
    expect(out).toMatch(/<option value="en" selected=""[^>]*>sub_lang_other:\{"name":"lang.en","count":3\}/)
    expect(out).toMatch(/<button[^>]*data-sub-translate[^>]*>.*translate_open/)
  })
  it("leere Sprache: Übersetzen gesperrt; während eines Auftrags: gesperrt", () => {
    const empty = html(<SubtitleLanguagePick list={{ film: "de", languages: [{ language: "de", count: 0 }] }} value="de" busy={false} onChange={noop} onTranslate={noop} />)
    expect(empty.match(/<button[^>]*data-sub-translate[^>]*>/)?.[0]).toContain('disabled=""')
    const busy = html(<SubtitleLanguagePick list={LIST} value="de" busy onChange={noop} onTranslate={noop} />)
    expect(busy.match(/<button[^>]*data-sub-translate[^>]*>/)?.[0]).toContain('disabled=""')
    expect(busy.match(/<select[^>]*>/)?.[0]).toContain('disabled=""')
  })
})

describe("6c – Dialog „Übersetzen“", () => {
  const dlg = (p: Partial<React.ComponentProps<typeof TranslateDialog>> = {}) =>
    html(<TranslateDialog list={LIST} from="de" count={3} model="" job={null} busy={false} onRun={noop} onClose={noop} {...p} />)
  it("Ausgangssprache, Zielsprachen ohne die Ausgangssprache, Anzahl, Modell, Kosten, Zeiten bleiben", () => {
    const out = dlg()
    expect(out).toContain('translate_from:{"name":"lang.de","count":3}')
    expect(out).not.toMatch(/<option value="de"/)
    expect(out).toMatch(/<option value="en"[^>]*>/)
    expect(out).toContain("translate_model_default")
    expect(dlg({ model: "openai/gpt-x" })).toContain("openai/gpt-x")
    expect(out).toContain("translate_cost")
    expect(out).toContain("translate_times")
  })
  it("Zielsprache mit Untertiteln: Hinweis aufs Ersetzen", () => {
    expect(dlg()).toContain('translate_replaces:{"count":3}')                       // erste Zielsprache ist en (vorhanden)
    expect(dlg({ list: { film: "de", languages: [{ language: "de", count: 3 }] } })).not.toContain("translate_replaces")
  })
  it("läuft: gesperrt mit Hinweis; Fehler mit Text", () => {
    const run = dlg({ job: job({ status: "running", result: null }) })
    expect(run.match(/<button[^>]*data-translate-run[^>]*>/)?.[0]).toContain('disabled=""')
    expect(run).toContain("translate_running")
    expect(dlg({ job: job({ status: "failed", error: "bad_answer" }) })).toContain("job_err.bad_answer_translate")
  })
})

describe("6c – Ausgabe: Untertitel mitliefern (abschaltbar, nicht eingebrannt)", () => {
  const R = (p: Partial<RenderItem>): RenderItem => ({ rel: "studio/renders/a.mp4", abs: "/w/a.mp4", name: "a.mp4", duration: 12, width: 1280, height: 720,
    created_at: "2026-10-18T10:00:00Z", missing: 0, clips: 3, subtitles: [], ...p })
  const clip = { id: "c", kind: "image" as const, start: 0, in: 0, out: 4, media_rel: "x", scene_id: "", shot_id: "", label: "l" }
  const panel = (p: Partial<React.ComponentProps<typeof DeliverPanel>> = {}) => html(<DeliverPanel clips={[clip]} aspect="16:9" renders={[]} job={null}
    busy={false} onRender={noop} onCut={noop} subtitleLanguages={["de", "en"]} withSubtitles={false} onWithSubtitles={noop} {...p} />)
  it("Kästchen mit den Sprachen, aus/an", () => {
    const off = panel()
    expect(off).toMatch(/<input[^>]*type="checkbox"[^>]*data-deliver-subtitles[^>]*>/)
    expect(off).toContain('deliver_subtitles:{"names":"lang.de, lang.en"}')
    expect(off.match(/<input[^>]*data-deliver-subtitles[^>]*>/)?.[0]).not.toContain("checked")
    expect(panel({ withSubtitles: true }).match(/<input[^>]*data-deliver-subtitles[^>]*>/)?.[0]).toContain('checked=""')
  })
  it("ohne Untertitel: kein Kästchen, Hinweis", () => {
    const none = panel({ subtitleLanguages: [] })
    expect(none).not.toContain("data-deliver-subtitles")
    expect(none).toContain("deliver_subtitles_none")
  })
  it("fertiger Film nennt seine Untertitelsprachen", () => {
    expect(panel({ renders: [R({ subtitles: ["de", "en"] })] })).toContain('deliver_film_subtitles:{"names":"lang.de, lang.en"}')
    expect(panel({ renders: [R({})] })).not.toContain("deliver_film_subtitles")
  })
})
