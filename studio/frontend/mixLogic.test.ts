import { describe, expect, it } from "vitest"
import TABLE from "./duckTable.test.json"
import {
  audibleTracks, clipGain, DUCK_DB, duckFactor, duckSpans, fadeFactor, fromDb, mixerOf, setClipMix, setDuck, setTrackMix, toDb,
} from "./mixLogic"
import type { Timeline, TimelineClip } from "./timelineApi"

const a = (p: Partial<TimelineClip>): TimelineClip => ({ id: "x", kind: "audio", start: 0, in: 0, out: 4, media_rel: "m.mp3",
  scene_id: "", shot_id: "", label: "M", ...p })
const TL: Timeline = { revision: 1, fps: 25, duck: true, tracks: [
  { id: "V1", kind: "video", clips: [] }, { id: "A1", kind: "audio", clips: [a({ id: "s", start: 2, out: 2 })] },
  { id: "A2", kind: "audio", gain_db: -6, clips: [a({ id: "m", out: 8, gain_db: 3, fade_in: 1, fade_out: 2 })] }] }

describe("5b – Ducking-Kurve (gleiche Tabelle wie der Server)", () => {
  it("Zeiträume zusammenlegen", () => {
    expect(duckSpans(TABLE.spans as [number, number][])).toEqual(TABLE.merged)
    expect(duckSpans([])).toEqual([])
  })
  it.each(TABLE.points)("t=%s → %s", (t, want) => {
    expect(duckFactor(TABLE.merged as [number, number][], t)).toBeCloseTo(want, 2)
  })
  it("Stärke wie auf dem Server", () => expect(DUCK_DB).toBe(-12))
})

describe("5b – Mischpult-Logik", () => {
  it("dB ↔ Faktor", () => {
    expect(fromDb(0)).toBe(1)
    expect(fromDb(-6)).toBeCloseTo(0.501, 3)
    expect(toDb(0.5)).toBeCloseTo(-6.02, 2)
    expect(toDb(0)).toBe(-Infinity)
  })

  it("wer klingt: Solo schlägt alles, sonst nicht stumm", () => {
    expect(audibleTracks({ V1: {}, A1: { mute: true }, A2: {} })).toEqual(new Set(["V1", "A2"]))
    expect(audibleTracks({ V1: {}, A1: { solo: true }, A2: { solo: true, mute: true } })).toEqual(new Set(["A1", "A2"]))
  })

  it("Blenden: linear in der Lautstärke, an den Rändern 0", () => {
    const c = a({ start: 0, out: 8, fade_in: 1, fade_out: 2 })
    expect(fadeFactor(c, 0)).toBe(0)
    expect(fadeFactor(c, 0.5)).toBeCloseTo(0.5)
    expect(fadeFactor(c, 3)).toBe(1)
    expect(fadeFactor(c, 7)).toBeCloseTo(0.5)
    expect(fadeFactor(a({ out: 8 }), 0)).toBe(1)
  })

  it("Lautstärke eines Tonclips bei t: Clip + Spur + Blende + Ducking", () => {
    const mx = mixerOf(TL)
    const m = TL.tracks[2].clips[0]
    expect(clipGain(mx, "A2", m, 4, [])).toBeCloseTo(fromDb(-3), 3)                       // −6 + 3, mitten im Clip
    expect(clipGain(mx, "A2", m, 0.5, [])).toBeCloseTo(fromDb(-3) * 0.5, 3)               // halb eingeblendet
    expect(clipGain(mx, "A2", m, 3, [[2, 4]])).toBeCloseTo(fromDb(-3) * fromDb(-12), 3)   // während Sprache
    expect(clipGain(mx, "A1", TL.tracks[1].clips[0], 3, [[2, 4]])).toBe(1)                 // Sprache selbst duckt nicht
    expect(clipGain({ ...mx, duck: false }, "A2", m, 3, [[2, 4]])).toBeCloseTo(fromDb(-3), 3)
    expect(clipGain({ ...mx, tracks: { ...mx.tracks, A2: { mute: true } } }, "A2", m, 4, [])).toBe(0)
  })

  it("Mischpult aus der Fassung lesen", () => {
    const mx = mixerOf(TL)
    expect(mx.tracks.A2).toEqual({ gain_db: -6 })
    expect(mx.tracks.V1).toEqual({})
    expect(mx.duck).toBe(true)
    expect(mixerOf({ ...TL, duck: undefined }).duck).toBe(true)                            // alter Server ohne Feld
    expect(mixerOf({ ...TL, duck: false }).duck).toBe(false)
  })

  it("Werte setzen: Standard fällt weg, Grenzen, Blenden nicht länger als der Clip, Rest bleibt gleich", () => {
    const t1 = setTrackMix(TL, "A2", { gain_db: 0 })
    expect("gain_db" in t1.tracks[2]).toBe(false)
    expect(setTrackMix(TL, "A1", { gain_db: 99 }).tracks[1].gain_db).toBe(12)
    expect(setTrackMix(TL, "A1", { gain_db: -99 }).tracks[1].gain_db).toBe(-60)
    expect(setTrackMix(TL, "V1", { mute: true }).tracks[0].mute).toBe(true)
    expect("mute" in setTrackMix(setTrackMix(TL, "V1", { mute: true }), "V1", { mute: false }).tracks[0]).toBe(false)
    const c = setClipMix(TL, "m", { fade_in: 7 }).tracks[2].clips[0]
    expect(c.fade_in).toBe(6)                                                               // 8 s − Ausblenden 2 s
    const d = setClipMix(TL, "m", { gain_db: 0, fade_out: 0 }).tracks[2].clips[0]
    expect("gain_db" in d || "fade_out" in d).toBe(false)
    expect(setClipMix(TL, "weg", { gain_db: 3 })).toBe(TL)
    expect(setDuck(TL, false).duck).toBe(false)
    expect(TL.tracks[2].gain_db).toBe(-6)                                                   // Eingabe unverändert
  })
})

describe("5b – Verlauf: Reglerbewegung = ein Schritt", () => {
  it("replaceTop ersetzt den letzten Stand, Rückgängig springt an den Anfang der Bewegung", async () => {
    const { History } = await import("./cutHistory")
    const h = new History<number>(0)
    h.push(1)
    h.push(2)                   // Regler gegriffen: erster Wert
    h.replaceTop(3)             // weiter gezogen
    h.replaceTop(4)
    expect(h.current).toBe(4)
    expect(h.undo()).toBe(1)
    expect(h.redo()).toBe(4)
    h.undo()
    h.replaceTop(9)             // ersetzen löscht Wiederholen
    expect(h.canRedo).toBe(false)
  })
})

describe("5b – Anzeige und Originalton", () => {
  it("dB-Text, Originalton-Faktor, Zahl der Clips", async () => {
    const { countsOf, dbText, originalGain } = await import("./mixLogic")
    expect(dbText(-3.5)).toBe("−3,5 dB")
    expect(dbText(2)).toBe("+2,0 dB")
    expect(dbText(0)).toBe("0,0 dB")
    expect(originalGain(mixerOf(TL))).toBe(1)
    expect(originalGain(mixerOf(setTrackMix(TL, "V1", { gain_db: -6 })))).toBeCloseTo(0.501, 3)
    expect(originalGain(mixerOf(setTrackMix(TL, "V1", { mute: true })))).toBe(0)
    expect(originalGain(mixerOf(setTrackMix(TL, "A2", { solo: true })))).toBe(0)                 // Solo woanders → Originalton aus
    expect(countsOf(TL)).toEqual({ V1: 0, A1: 1, A2: 1 })
    expect(countsOf(null)).toEqual({ V1: 0, A1: 0, A2: 0 })
  })
})
