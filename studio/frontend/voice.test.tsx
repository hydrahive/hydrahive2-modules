import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import { isBatch, jobText } from "./jobLogic"
import { BATCH_KINDS, type Job, type Shot } from "./planApi"
import { ShotForm } from "./ShotForm"
import { ShotSpeech } from "./ShotSpeech"

const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const noop = () => {}
const shot = (p: Partial<Shot> = {}): Shot => ({ id: "s1", order: 0, shot: "", prompt: "Ole", element_ids: [], duration: 4, status: "planned",
  image_rel: null, video_rel: null, variants: [], speech: "", voice: "", voice_rel: null, ...p })
const job = (p: Partial<Job>): Job => ({ id: "j", kind: "speech", target: "s1", scene_id: "sc", status: "running", error: null, result: null,
  created_at: "x", finished_at: null, ...p })

describe("5c-1 – Sprechtext im Shot", () => {
  it("Formular hat Sprechtext und Stimme; Speichern schickt beides mit", () => {
    const out = html(<ShotForm shot={shot({ speech: "Da ist er!", voice: "af_bella" })} index={0} elements={[]} sceneElementIds={[]} presets={[]}
      busy={false} onSave={noop} onDelete={noop} voices={["af_bella", "af_nicole"]} />)
    expect(out).toContain('data-field="speech"')
    expect(out).toContain("Da ist er!")
    expect(out).toMatch(/<select[^>]*data-shot-voice/)
    expect(out).toMatch(/<option value="af_bella" selected="">af_bella<\/option>/)
    expect(out).toContain('<option value="">voice_default</option>')
  })

  it("ohne Stimmen des Modells: kein Auswahlfeld, Hinweis „Standardstimme“", () => {
    const out = html(<ShotForm shot={shot()} index={0} elements={[]} sceneElementIds={[]} presets={[]} busy={false} onSave={noop} onDelete={noop} voices={[]} />)
    expect(out).not.toContain("data-shot-voice")
    expect(out).toContain("voice_only_default")
  })

  it("Knopf „Sprache erzeugen“: gesperrt ohne Text, läuft, fertig mit Abspieler, Fehler mit Text", () => {
    const none = html(<ShotSpeech shot={shot()} base="/w" job={null} onGenerate={noop} />)
    expect(none.match(/<button[^>]*data-shot-speech-generate[^>]*>/)?.[0]).toContain('disabled=""')
    expect(none).toContain("speech_needs_text")
    const ready = html(<ShotSpeech shot={shot({ speech: "Hallo" })} base="/w" job={null} onGenerate={noop} />)
    expect(ready.match(/<button[^>]*data-shot-speech-generate[^>]*>/)?.[0]).not.toContain('disabled=""')
    expect(ready).toContain("speech_generate")
    expect(html(<ShotSpeech shot={shot({ speech: "Hallo" })} base="/w" job={job({})} onGenerate={noop} />)).toContain("speech_running")
    const done = html(<ShotSpeech shot={shot({ speech: "Hallo", voice_rel: "studio/media/voice/a.wav" })} base="/w" job={null} onGenerate={noop} />)
    expect(done).toMatch(/<audio[^>]*src="\/f\/w\/studio\/media\/voice\/a.wav"/)
    expect(done).toContain("speech_again")
    const fail = html(<ShotSpeech shot={shot({ speech: "Hallo" })} base="/w" job={job({ status: "failed", error: "bad_audio" })} onGenerate={noop} />)
    expect(fail).toContain("job_err.bad_audio")
    expect(fail).toContain("speech_cost")
  })

  it("Sammelauftrag „Sprache für alle Shots mit Sprechtext“, Fehlertexte für Ton", () => {
    expect(BATCH_KINDS).toContain("speech_all")
    expect(isBatch(job({ kind: "speech_all" }))).toBe(true)
    expect(isBatch(job({ kind: "speech" }))).toBe(false)
    const t = (k: string) => k
    expect(jobText(t, job({ status: "failed", error: "bad_audio" }))).toBe("job_err.bad_audio")
    expect(jobText(t, job({ status: "failed", error: "no_text" }))).toBe("job_err.no_text")
    expect(jobText(t, job({ kind: "speech", status: "failed", error: "no_key" }))).toBe("job_err.no_key_voice")
    expect(jobText(t, job({ kind: "image", status: "failed", error: "no_key" }))).toBe("job_err.no_key")
  })
})

describe("5c-1 – gebundene Sprache in den Eigenschaften", () => {
  it("Hinweis und „Vom Shot lösen“ nur bei gebundener Sprache", async () => {
    const { CutInspector } = await import("./CutInspector")
    const clip = { id: "v", kind: "audio" as const, start: 0, in: 0, out: 2, media_rel: "studio/media/voice/a.wav", scene_id: "", shot_id: "s1", label: "Hallo" }
    const out = html(<CutInspector clip={clip} onPlan={noop} onUnbind={noop} />)
    expect(out).toContain("cut_voice_bound")
    expect(out).toContain("data-cut-unbind")
    const free = html(<CutInspector clip={{ ...clip, shot_id: "" }} onPlan={noop} onUnbind={noop} />)
    expect(free).not.toContain("cut_voice_bound")
    expect(html(<CutInspector clip={{ ...clip, kind: "image" }} onPlan={noop} onUnbind={noop} />)).not.toContain("cut_voice_bound")
  })
})
