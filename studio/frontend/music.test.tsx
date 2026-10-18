import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import type { Tracks } from "./cutTracks"
import { MusicForm } from "./MusicForm"
import { finishedMusic, musicClip, placeMusic, type MusicDefaults } from "./musicLogic"
import { jobText } from "./jobLogic"
import { MixerPanel } from "./MixerPanel"
import { mixerOf } from "./mixLogic"
import type { Job } from "./planApi"
import type { TimelineClip } from "./timelineApi"

const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const noop = () => {}
const FPS = 25
const c = (p: Partial<TimelineClip>): TimelineClip => ({ id: "x", kind: "image", start: 0, in: 0, out: 4, media_rel: "a.png", scene_id: "", shot_id: "", label: "x", ...p })
const TR: Tracks = {
  V1: [c({ id: "p1", scene_id: "s1", out: 4 }), c({ id: "p2", start: 4, scene_id: "s2", out: 6 }), c({ id: "p3", start: 10, scene_id: "s2", out: 3 })],
  A1: [],
  A2: [c({ id: "m0", kind: "audio", start: 0, out: 2, media_rel: "x.mp3" })],
}
const job = (p: Partial<Job>): Job => ({ id: "j1", kind: "music", target: "music:p", scene_id: "", status: "done", error: null,
  result: { rel: "studio/media/music/a.mp3", duration: 30, seconds: 20, scene_id: "" }, created_at: "x", finished_at: "y", ...p })
const DEF: MusicDefaults = { model: "google/lyria", film: { description: "Fischer kehrt heim", seconds: 13 },
  scenes: [{ id: "s1", title: "Hafen", description: "Morgen", seconds: 4 }, { id: "s2", title: "Sturm", description: "Gewitter", seconds: 9 }] }

describe("5c-2 – Musik auf die Zeitleiste", () => {
  it("Clip aus dem Ergebnis: gekürzt auf die gewünschte Länge, dann 2 s Ausblenden", () => {
    const m = musicClip(job({}).result as never, () => "n")!
    expect(m).toMatchObject({ kind: "audio", in: 0, out: 20, media_rel: "studio/media/music/a.mp3", fade_out: 2 })
    const short = musicClip({ rel: "b.mp3", duration: 12, seconds: 20, scene_id: "" }, () => "n")!
    expect(short.out).toBe(12)
    expect(short.fade_out).toBeUndefined()                                  // nicht gekürzt → keine Blende
    expect(musicClip({ rel: "", duration: 0, seconds: 0, scene_id: "" }, () => "n")).toBeNull()
    expect(musicClip({ rel: "c.mp3", duration: 0, seconds: 20, scene_id: "" }, () => "n")).toBeNull()        // Länge unbekannt → nicht ablegen
  })

  it("Platz: Film ab 0 (belegt → nächste freie Stelle), Szene ab ihrem ersten Bildclip, unbekannte Szene → Abspielkopf", () => {
    const m = musicClip({ rel: "a.mp3", duration: 5, seconds: 5, scene_id: "" }, () => "n")!
    expect(placeMusic(TR, m, "", 7, FPS).A2.find((x) => x.id === "n")?.start).toBe(2)
    const s = musicClip({ rel: "a.mp3", duration: 5, seconds: 5, scene_id: "s2" }, () => "n")!
    expect(placeMusic(TR, s, "s2", 7, FPS).A2.find((x) => x.id === "n")?.start).toBe(4)
    const gone = musicClip({ rel: "a.mp3", duration: 5, seconds: 5, scene_id: "weg" }, () => "n")!
    expect(placeMusic(TR, gone, "weg", 7, FPS).A2.find((x) => x.id === "n")?.start).toBe(7)
    expect(placeMusic(TR, m, "", 7, FPS).V1).toBe(TR.V1)
  })

  it("fertig: nur Aufträge aus diesem Fenster (beim Öffnen liegt alte Musik schon in der Bibliothek)", () => {
    const pending = new Set(["j1", "j2"])
    expect(finishedMusic([job({ status: "running" })], pending)).toBeNull()
    expect(finishedMusic([job({ id: "j9" })], pending)).toBeNull()
    expect(finishedMusic([job({ id: "j3", kind: "speech" }), job({})], pending)?.id).toBe("j1")
    expect(finishedMusic([job({ id: "j2", status: "failed", error: "no_key", result: null })], pending)?.status).toBe("failed")
    expect(finishedMusic([job({ id: "j2", kind: "speech" })], pending)).toBeNull()
  })

  it("Fehlertexte für Musik nennen Musik, nicht Bild oder Sprache", () => {
    const t = (k: string) => k
    for (const e of ["no_key", "provider_rejected", "empty_answer", "bad_audio"]) expect(jobText(t, job({ status: "failed", error: e, result: null }))).toBe(`job_err.${e}_music`)
    expect(jobText(t, job({ status: "failed", error: "provider_unreachable", result: null }))).toBe("job_err.provider_unreachable")
  })
})

describe("5c-2 – Formular „Musik erzeugen“", () => {
  const form = (p: Partial<React.ComponentProps<typeof MusicForm>> = {}) =>
    html(<MusicForm defaults={DEF} job={null} busy={false} onRun={noop} onClose={noop} {...p} />)
  it("Ziel, Beschreibung (vorbelegt), Länge, Modell, Kosten-Hinweis, Starten", () => {
    const out = form()
    expect(out).toContain("music_target")
    expect(out).toContain('<option value="" selected="">music_film</option>')
    expect(out).toContain('<option value="s2">Sturm</option>')
    expect(out).toContain("Fischer kehrt heim")
    expect(out).toMatch(/type="number"[^>]*value="13"/)
    expect(out).toContain("google/lyria")
    expect(out).toContain("music_cost")
    expect(out).toContain("data-music-run")
  })
  it("läuft gerade: Knopf gesperrt mit Hinweis; Fehler mit Text", () => {
    const run = form({ job: job({ status: "running", result: null }) })
    expect(run.match(/<button[^>]*data-music-run[^>]*>/)?.[0]).toContain('disabled=""')
    expect(run).toContain("music_running")
    expect(form({ job: job({ status: "failed", error: "empty_answer", result: null }) })).toContain("job_err.empty_answer_music")
  })
  it("ohne Vorbelegung (lädt): Hinweis", () => {
    expect(html(<MusicForm defaults={null} job={null} busy={false} onRun={noop} onClose={noop} />)).toContain("loading")
  })
})

describe("5c-2 – Einstieg im Mischpult", () => {
  const panel = (p: Partial<React.ComponentProps<typeof MixerPanel>> = {}) => html(<MixerPanel mixer={mixerOf(null)} counts={{ V1: 0, A1: 0, A2: 0 }}
    playing={false} onTrack={noop} onDuck={noop} onMusic={noop} musicRunning={false} {...p} />)
  it("Knopf „Musik erzeugen …“; läuft ein Auftrag: gesperrt mit Hinweis", () => {
    expect(panel()).toMatch(/<button[^>]*data-music-open[^>]*>.*music_open/)
    const run = panel({ musicRunning: true })
    expect(run.match(/<button[^>]*data-music-open[^>]*>/)?.[0]).toContain('disabled=""')
    expect(run).toContain("music_running")
  })
})
