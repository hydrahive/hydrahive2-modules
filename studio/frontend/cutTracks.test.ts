import { describe, expect, it } from "vitest"
import { addMedia, canSplit, editTracks, moveAudioClip, moveVideoClip, toTimeline, trackOf, tracksOf, trimTracks, type Tracks } from "./cutTracks"
import type { Timeline, TimelineClip } from "./timelineApi"

const FPS = 25
let n = 0
const newId = () => `n${++n}`
const c = (p: Partial<TimelineClip>): TimelineClip => ({ id: "x", kind: "image", start: 0, in: 0, out: 5, media_rel: "studio/media/images/a.png",
  scene_id: "", shot_id: "", label: "x", ...p })
const au = (p: Partial<TimelineClip>) => c({ kind: "audio", media_rel: "atelier/audio/m.mp3", ...p })
const TR: Tracks = {
  V1: [c({ id: "v1", out: 4 }), c({ id: "v2", start: 4, out: 4 })],                      // 0–4, 4–8
  A1: [au({ id: "s1", start: 1, out: 2 })],                                                // 1–3
  A2: [au({ id: "m1", start: 0, out: 6 })],                                                // 0–6
}
const ctx = (selected: string | null, time = 2) => ({ selected, time, fps: FPS, newId })
const lay = (cs: TimelineClip[]) => [...cs].sort((a, b) => a.start - b.start).map((x) => `${x.id}@${x.start}+${x.out - x.in}`).join(" ")

describe("5a – Bearbeiten über alle Spuren", () => {
  it("Spuren aus der Fassung und zurück; fehlende Tonspuren (alter Server) kommen leer dazu", () => {
    const old: Timeline = { revision: 1, fps: 25, tracks: [{ id: "V1", kind: "video", clips: TR.V1 }] }
    expect(tracksOf(old)).toEqual({ V1: TR.V1, A1: [], A2: [] })
    const tl = toTimeline(old, TR)
    expect(tl.tracks.map((t) => `${t.id}:${t.kind}:${t.clips.length}`)).toEqual(["V1:video:2", "A1:audio:1", "A2:audio:1"])
    expect(tl.revision).toBe(1)
    expect(tracksOf(null)).toEqual({ V1: [], A1: [], A2: [] })
  })

  it("Spur eines Clips", () => {
    expect(trackOf(TR, "v2")).toBe("V1")
    expect(trackOf(TR, "s1")).toBe("A1")
    expect(trackOf(TR, "m1")).toBe("A2")
    expect(trackOf(TR, "weg")).toBeNull()
    expect(trackOf(TR, null)).toBeNull()
  })

  it("Teilen wirkt auf die Spur des gewählten Clips, ohne Auswahl auf V1; die anderen Spuren bleiben unberührt", () => {
    const a = editTracks(TR, { kind: "split" }, ctx("m1", 2))
    expect(a.A2).toHaveLength(2)
    expect(a.V1).toBe(TR.V1)
    expect(a.A1).toBe(TR.A1)
    const v = editTracks(TR, { kind: "split" }, ctx(null, 2))
    expect(v.V1).toHaveLength(3)
    expect(v.A2).toBe(TR.A2)
    expect(canSplit(TR, ctx("s1", 5))).toBe(false)                    // Abspielkopf in der Lücke der Sprachspur
    expect(canSplit(TR, ctx("s1", 2))).toBe(true)
  })

  it("Löschen: auf der Tonspur bleibt die Lücke, auf V1 rückt der Rest nach", () => {
    expect(lay(editTracks(TR, { kind: "delete" }, ctx("s1")).A1)).toBe("")
    expect(lay(editTracks(TR, { kind: "delete" }, ctx("v1")).V1)).toBe("v2@0+4")
    expect(editTracks(TR, { kind: "delete" }, ctx(null))).toBe(TR)
  })

  it("Q/W und Verdoppeln auf der Tonspur", () => {
    expect(lay(editTracks(TR, { kind: "split-keep", drop: "right" }, ctx("m1", 2)).A2)).toBe("m1@0+2")
    const d = editTracks(TR, { kind: "duplicate" }, ctx("s1"))
    expect(lay(d.A1)).toMatch(/^s1@1\+2 n\d+@3\+2$/)
  })

  it("Einfügen: Ton an den Abspielkopf auf seine Spur (an freier Stelle), Bild hinter den gewählten V1-Clip", () => {
    const a = editTracks(TR, { kind: "paste" }, ctx("v1", 10), { clip: TR.A1[0], track: "A1" })
    expect(lay(a.A1)).toMatch(/^s1@1\+2 n\d+@10\+2$/)
    const v = editTracks(TR, { kind: "paste" }, ctx("v1"), { clip: TR.V1[1], track: "V1" })
    expect(v.V1.map((x) => x.start)).toEqual([0, 4, 8])
    expect(editTracks(TR, { kind: "paste" }, ctx("v1"), null)).toBe(TR)
  })

  it("Kürzen findet die Spur selbst", () => {
    expect(lay(trimTracks(TR, "m1", "end", -2, FPS, {}).A2)).toBe("m1@0+4")
    expect(lay(trimTracks(TR, "v1", "end", -1, FPS, {}).V1)).toBe("v1@0+3 v2@3+4")      // magnetisch
    expect(trimTracks(TR, "weg", "end", 1, FPS, {})).toBe(TR)
  })

  it("Tonclip verschieben, auch auf die andere Tonspur; Bildclips gehen nicht auf Tonspuren", () => {
    expect(lay(moveAudioClip(TR, "s1", "A1", 7, FPS).A1)).toBe("s1@7+2")
    const x = moveAudioClip(TR, "s1", "A2", 1, FPS)
    expect(x.A1).toEqual([])
    expect(lay(x.A2)).toBe("m1@0+6 s1@6+2")                                              // rückt hinter die Musik
    expect(moveAudioClip(TR, "v1", "A2", 9, FPS)).toBe(TR)
    expect(moveVideoClip(TR, "s1", 0, FPS)).toBe(TR)
    expect(lay(moveVideoClip(TR, "v2", 0, FPS).V1)).toBe("v2@0+4 v1@4+4")
  })

  it("Aus der Bibliothek: Musik → „Musik“, Sprache → „Sprache“, auf Wunsch auf die andere; Bild an Stelle auf V1", () => {
    const m = addMedia(TR, { kind: "music", rel: "tonstudio/clips/l.mp3", name: "Lied", duration: 3 }, { time: 7 }, FPS, newId)!
    expect(lay(m.tracks.A2)).toBe(`m1@0+6 ${m.clip.id}@7+3`)
    expect(m.clip.start).toBe(7)
    const s = addMedia(TR, { kind: "audio", rel: "atelier/audio/s.wav", name: "S", duration: 1 }, { time: 2 }, FPS, newId)!
    expect(lay(s.tracks.A1)).toBe(`s1@1+2 ${s.clip.id}@3+1`)                             // läge auf s1 → dahinter
    expect(s.clip.start).toBe(3)
    const o = addMedia(TR, { kind: "music", rel: "x.mp3", name: "X", duration: 1 }, { time: 8, track: "A1" }, FPS, newId)!
    expect(o.tracks.A1).toHaveLength(2)
    const i = addMedia(TR, { kind: "image", rel: "studio/media/images/b.png", name: "B" }, { index: 0, time: 0 }, FPS, newId)!
    expect(i.tracks.V1[0].id).toBe(i.clip.id)
    expect(addMedia(TR, { kind: "element", rel: "x", name: "F" }, { time: 0 }, FPS, newId)).toBeNull()
  })
})
