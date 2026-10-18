import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { CutInspector } from "./CutInspector"
import { CutTimeline } from "./CutTimeline"
import { Waveform } from "./Waveform"
import { deliverSummary } from "./deliverLogic"
import { allClips, clipsOf, findClip, withTrack, type Timeline, type TimelineClip } from "./timelineApi"
import { slicePeaks } from "./waveLogic"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const attr = (out: string, name: string) => [...out.matchAll(new RegExp(`${name}="([^"]+)"`, "g"))].map((m) => m[1])
const clip = (p: Partial<TimelineClip>): TimelineClip => ({ id: "c", kind: "image", start: 0, in: 0, out: 4, media_rel: "studio/media/images/a.png",
  scene_id: "", shot_id: "", label: "x", ...p })
const MUSIC = clip({ id: "m1", kind: "audio", start: 2, in: 1, out: 11, media_rel: "atelier/audio/lied.mp3", label: "Lied" })   // 2–12
const VOICE = clip({ id: "s1", kind: "audio", start: 1, out: 2, media_rel: "tonstudio/clips/satz.wav", label: "Satz" })
const TL: Timeline = { revision: 2, fps: 25, tracks: [
  { id: "V1", kind: "video", clips: [clip({ id: "v1" })] }, { id: "A1", kind: "audio", clips: [VOICE] }, { id: "A2", kind: "audio", clips: [MUSIC] }] }
const timeline = (tl: Timeline, p: Partial<React.ComponentProps<typeof CutTimeline>> = {}) => html(<CutTimeline timeline={tl} base="/w" time={0}
  view={{ start: 0, span: 20 }} selected={null} busy={false} onView={noop} onSeek={noop} onSelect={noop} onFromPlan={noop} {...p} />)
const audioEdit = { onMove: noop, onTrim: noop, onDrop: noop, snapTo: [], edges: [] }

describe("5a – Tonspuren in der Zeitleiste", () => {
  it("Spuren Bild, Sprache, Musik; Tonclips an ihrer Stelle (Lücken bleiben), Filmlänge über alle Spuren", () => {
    const out = timeline(TL)
    expect(attr(out, "data-studio-track")).toEqual(["video", "voice", "music"])
    expect(out).toContain("cut_track_voice")
    expect(out).toContain("cut_track_music")
    expect(out).toMatch(/data-cut-clip="m1"[^>]*style="left:10%;width:50%"/)       // 2 s von 20, 10 s lang
    expect(out).toMatch(/data-cut-clip="s1"[^>]*style="left:5%;width:10%"/)          // 1–3 s
    expect(out).toContain('data-cut-length="12"')                                // Musik endet nach dem Bild
    expect(out).toContain('cut_count:{"count":3}')
  })

  it("Leere Zeitleiste: Hinweis, und die Spuren sind trotzdem da (zum Hineinziehen)", () => {
    const empty = withTrack(withTrack(withTrack(TL, "V1", []), "A1", []), "A2", [])
    const out = timeline(empty, { audio: audioEdit })
    expect(out).toContain("cut_empty")
    expect(attr(out, "data-cut-audio-lane")).toEqual(["A1", "A2"])
    expect(out.match(/cut_audio_empty/g)).toHaveLength(2)
  })

  it("Nur Ton (ohne Bild) zählt als Inhalt: kein Leer-Hinweis, Übersicht da", () => {
    const out = timeline(withTrack(TL, "V1", []))
    expect(out).not.toContain("cut_empty")
    expect(out).toContain("data-studio-overview")
  })

  it("Bearbeiten: Tonclips ziehbar mit Griffen; ohne Bearbeiten nur ansehen", () => {
    const ed = timeline(TL, { audio: audioEdit })
    expect(ed).toMatch(/data-cut-clip="m1"[^>]*draggable="true"/)
    expect(ed).toContain('data-cut-trim="m1:start"')
    expect(ed).toContain('data-cut-trim="s1:end"')
    const view = timeline(TL)
    expect(view).toMatch(/data-cut-clip="m1"[^>]*draggable="false"/)
    expect(view).not.toContain('data-cut-trim="m1:start"')
  })

  it("Gelöschter Ton: Clip bleibt rot gestrichelt mit „Ton fehlt“, ohne Wellenform", () => {
    const gone = withTrack(TL, "A2", [{ ...MUSIC, media_rel: "", missing: true }])
    const out = timeline(gone, { waveforms: { "atelier/audio/lied.mp3": [50, 50] } })
    expect(out).toMatch(/data-cut-clip="m1"[^>]*data-missing="1"/)
    expect(out).toContain("cut_audio_missing")
  })

  it("Wellenform: geladen als Balken, sonst flache Linie", () => {
    const peaks = Array.from({ length: 600 }, (_, i) => (i % 10) * 10)
    const out = timeline(TL, { waveforms: { "atelier/audio/lied.mp3": peaks } })
    expect(out).toMatch(/data-cut-clip="m1"[\s\S]*?data-waveform="120"/)          // 10 s × 50 = 500 Werte → 120 Balken
    expect(out).toMatch(/data-cut-clip="s1"[\s\S]*?data-waveform="flat"/)        // noch nicht geladen
  })

  it("Eigenschaften eines Tonclips: Art „Ton“, Stelle im Ton, Hinweis bei gelöschtem Ton", () => {
    const i = html(<CutInspector clip={MUSIC} onPlan={noop} />)
    expect(i).toContain("cut_kind.audio")
    expect(i).toContain("cut_from_sound")
    expect(i).not.toContain("cut_to_plan")
    expect(html(<CutInspector clip={{ ...MUSIC, missing: true }} onPlan={noop} />)).toContain("cut_audio_missing_hint")
  })
})

describe("5a – Hilfen", () => {
  it("Spuren lesen und ersetzen; alte Fassung ohne Tonspuren", () => {
    expect(clipsOf(TL, "A2")).toEqual([MUSIC])
    expect(clipsOf(TL)).toHaveLength(1)
    const old: Timeline = { revision: 1, fps: 25, tracks: [{ id: "V1", kind: "video", clips: [clip({})] }] }
    expect(clipsOf(old, "A1")).toEqual([])
    expect(withTrack(old, "A2", [MUSIC]).tracks.map((t) => t.id)).toEqual(["V1", "A1", "A2"])
    expect(allClips(TL).map((c) => c.id)).toEqual(["v1", "s1", "m1"])
    expect(allClips(null)).toEqual([])
    expect(findClip(TL, "m1")).toBe(MUSIC)                             // gewählter Tonclip → Eigenschaften rechts
    expect(findClip(TL, "v1")?.id).toBe("v1")
    expect(findClip(TL, "weg")).toBeNull()
    expect(findClip(TL, null)).toBeNull()
    expect(findClip(null, "m1")).toBeNull()
  })

  it("Ausgabe-Übersicht zählt alle Spuren, Länge bis zum letzten Ton", () => {
    expect(deliverSummary(allClips(TL))).toMatchObject({ seconds: 12, clips: 3, placeholders: 0 })
  })

  it("Wellenform-Ausschnitt: nur in–out, verdichtet auf den höchsten Wert", () => {
    const p = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    expect(slicePeaks(p, 2, 1, 3)).toEqual([3, 4, 5, 6])                         // 2 Werte je s: 1–3 s → Index 2–5
    expect(slicePeaks(p, 2, 0, 5, 2)).toEqual([5, 10])
    expect(slicePeaks([], 2, 0, 1)).toEqual([])
    expect(slicePeaks(p, 2, 3, 3)).toEqual([])
    expect(html(<Waveform peaks={[]} perSecond={50} from={0} to={1} />)).toContain('data-waveform="flat"')
  })
})

describe("5a – Ablegen aus der Bibliothek", () => {
  it("Ton landet auf der Spur, auf die er gezogen wird; Bild auf V1 an Stelle und Zeit; Figuren → Hinweis", async () => {
    const { appendNotice, cutDrops, edgesOf } = await import("./cutWiring")
    const add = vi.fn((it: { kind: string }) => it.kind !== "element")
    const items = [{ id: "m", kind: "music" }, { id: "i", kind: "image" }, { id: "f", kind: "element" }] as never
    const notice = vi.fn()
    const d = cutDrops(items, { move: noop, onTrim: noop, moveAudio: noop, addMedia: add, snapTo: [3], snap: true }, [MUSIC], notice)
    d.audio.onDrop("m", "A1", 4)
    expect(add).toHaveBeenLastCalledWith(items[0], undefined, 4, "A1")
    d.audio.onDrop("i", "A2", 4)                                      // Bild auf eine Tonspur gezogen → auf V1 statt auf A2
    expect(add).toHaveBeenLastCalledWith(items[1], undefined, 4, undefined)
    d.edit.onDrop("i", 1, 6)
    expect(add).toHaveBeenLastCalledWith(items[1], 1, 6)
    d.edit.onDrop("f", 0, 0)
    expect(notice).toHaveBeenCalledTimes(1)
    d.edit.onDrop("weg", 0, 0)
    expect(notice).toHaveBeenCalledTimes(1)
    expect(d.audio.edges).toEqual([2, 12])
    expect(cutDrops(items, { move: noop, onTrim: noop, moveAudio: noop, addMedia: add, snapTo: [], snap: false }, [MUSIC], notice).audio.edges).toEqual([])
    expect(edgesOf([clip({ start: 1, in: 1, out: 3 })])).toEqual([1, 3])
    expect(appendNotice(items[0], add)).toBe("cut_notice_sound")
    expect(appendNotice(items[1], add)).toBe("cut_notice_appended")
    expect(appendNotice(items[2], add)).toBeNull()
    expect(appendNotice(null, add)).toBeNull()
  })
})
