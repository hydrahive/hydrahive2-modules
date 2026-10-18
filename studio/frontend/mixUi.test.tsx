import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { CutInspector } from "./CutInspector"
import { CutTimeline } from "./CutTimeline"
import { MixerPanel } from "./MixerPanel"
import { MixInspector } from "./MixInspector"
import { mixerOf, setTrackMix } from "./mixLogic"
import type { Timeline, TimelineClip } from "./timelineApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const a = (p: Partial<TimelineClip>): TimelineClip => ({ id: "x", kind: "audio", start: 0, in: 0, out: 10, media_rel: "m.mp3",
  scene_id: "", shot_id: "", label: "Lied", ...p })
const MUSIC = a({ id: "m1", gain_db: -4.5, fade_in: 2, fade_out: 1 })
const TL: Timeline = { revision: 1, fps: 25, tracks: [
  { id: "V1", kind: "video", clips: [] }, { id: "A1", kind: "audio", clips: [] }, { id: "A2", kind: "audio", gain_db: -6, clips: [MUSIC] }] }
const panel = (tl: Timeline, p: Partial<React.ComponentProps<typeof MixerPanel>> = {}) =>
  html(<MixerPanel mixer={mixerOf(tl)} counts={{ V1: 0, A1: 0, A2: 1 }} playing={false} onTrack={noop} onDuck={noop} {...p} />)
const btnOf = (out: string, attr: string) => out.match(new RegExp(`<button[^>]*${attr}[^>]*>`))?.[0] ?? ""

describe("5b – Mischpult", () => {
  it("drei Kanäle mit Regler, dB-Anzeige, Stumm, Solo, Pegel und Clip-Zahl", () => {
    const out = panel(TL)
    for (const id of ["V1", "A1", "A2"]) {
      expect(out).toContain(`data-mix-channel="${id}"`)
      expect(out).toContain(`data-mix-gain="${id}"`)
      expect(out).toContain(`data-mix-meter="${id}"`)
    }
    for (const k of ["mix_original", "mix_voice", "mix_music", "mix_mute", "mix_solo", "mix_title"]) expect(out).toContain(k)
    expect(out).toMatch(/data-mix-db="A2"[^>]*>−6,0 dB/)
    expect(out).toMatch(/data-mix-db="V1"[^>]*>0,0 dB/)
    expect(out).toContain('mix_clips:{"count":1}')
    expect(out).toContain('aria-label="mix_volume_of:{"name":"mix_music"}"')
  })

  it("Stumm/Solo gedrückt; nicht hörbare Kanäle sind gekennzeichnet", () => {
    const muted = panel(setTrackMix(TL, "A1", { mute: true }))
    expect(btnOf(muted, 'data-mix-mute="A1"')).toContain('aria-pressed="true"')
    expect(btnOf(muted, 'data-mix-mute="A2"')).toContain('aria-pressed="false"')
    expect(muted).not.toMatch(/data-mix-channel="A1"[^>]*data-mix-live/)
    expect(muted).toMatch(/data-mix-channel="A2"[^>]*data-mix-live="1"/)
    const solo = panel(setTrackMix(TL, "A2", { solo: true }))
    expect(btnOf(solo, 'data-mix-solo="A2"')).toContain('aria-pressed="true"')
    expect(solo).not.toMatch(/data-mix-channel="V1"[^>]*data-mix-live/)
  })

  it("Schalter „Musik leiser, wenn gesprochen wird“ zeigt den Stand", () => {
    const duck = (o: string) => o.match(/<input[^>]*data-mix-duck[^>]*>/)?.[0] ?? ""
    expect(duck(panel(TL))).toContain('checked=""')
    expect(duck(panel({ ...TL, duck: false }))).not.toContain("checked")
    expect(panel(TL)).toContain("mix_duck")
  })
})

describe("5b – Eigenschaften eines Tonclips", () => {
  it("Lautstärke und Blenden; ohne Tonclip ein Hinweis", () => {
    const out = html(<MixInspector clip={MUSIC} onChange={noop} />)
    expect(out).toContain("data-clip-gain")
    expect(out).toContain("−4,5 dB")
    expect(out).toMatch(/data-clip-fade="fade_in" value="2"/)
    expect(out).toMatch(/data-clip-fade="fade_out" value="1"/)
    expect(out).toContain('max="10"')
    expect(html(<MixInspector clip={null} onChange={noop} />)).toContain("mix_pick_clip")
    expect(html(<MixInspector clip={a({ kind: "image" })} onChange={noop} />)).toContain("mix_pick_clip")
  })

  it("auch im Reiter „Schneiden“ rechts beim Tonclip", () => {
    expect(html(<CutInspector clip={MUSIC} onPlan={noop} mix={noop} />)).toContain("data-clip-mix")
    expect(html(<CutInspector clip={MUSIC} onPlan={noop} />)).not.toContain("data-clip-mix")
  })
})

describe("5b – Zeitleiste zeigt das Mischpult", () => {
  const timeline = (tl: Timeline) => html(<CutTimeline timeline={tl} base="/w" time={0} view={{ start: 0, span: 20 }} selected={null} busy={false}
    onView={noop} onSeek={noop} onSelect={noop} onFromPlan={noop} mixer={mixerOf(tl)} />)
  it("stumme bzw. nicht im Solo liegende Tonspur blass mit Hinweis", () => {
    const out = timeline(setTrackMix(TL, "A2", { mute: true }))
    expect(out).toMatch(/data-studio-track="music"[^>]*data-track-silent="1"/)
    expect(out).toContain("mix_track_silent")
    expect(timeline(TL)).not.toContain("data-track-silent")
    expect(timeline(setTrackMix(TL, "A2", { solo: true }))).toMatch(/data-studio-track="voice"[^>]*data-track-silent="1"/)
  })
  it("Blenden als Schräge am Clip, Breite im Verhältnis zur Cliplänge", () => {
    const out = timeline(TL)
    expect(out).toMatch(/style="width:20%"[^>]*data-fade="in"/)
    expect(out).toMatch(/style="width:10%"[^>]*data-fade="out"/)
  })
})
