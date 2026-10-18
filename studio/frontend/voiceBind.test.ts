import { describe, expect, it } from "vitest"
import type { Tracks } from "./cutTracks"
import type { TimelineClip } from "./timelineApi"
import { followPictures, unbind } from "./voiceBind"

const FPS = 25
const c = (p: Partial<TimelineClip>): TimelineClip => ({ id: "x", kind: "image", start: 0, in: 0, out: 4, media_rel: "a.png", scene_id: "", shot_id: "", label: "x", ...p })
const v = (p: Partial<TimelineClip>) => c({ kind: "audio", media_rel: "studio/media/voice/a.wav", ...p })
const lay = (cs: TimelineClip[]) => [...cs].sort((a, b) => a.start - b.start).map((x) => `${x.id}@${x.start}+${Math.round((x.out - x.in) * 100) / 100}`).join(" ")
const BASE: Tracks = {
  V1: [c({ id: "p1", shot_id: "s1", out: 4 }), c({ id: "p2", start: 4, shot_id: "s2", out: 3 })],
  A1: [v({ id: "v1", shot_id: "s1", out: 2 }), v({ id: "v2", start: 4, shot_id: "s2", out: 2.5 }), v({ id: "f", start: 9, out: 1 })],
  A2: [],
}

describe("5c – Sprache folgt ihrem Bildclip", () => {
  it("Umsortieren auf V1: gebundene Sprache wandert an den neuen Anfang, freie bleibt", () => {
    const moved: Tracks = { ...BASE, V1: [c({ id: "p2", start: 0, shot_id: "s2", out: 3 }), c({ id: "p1", start: 3, shot_id: "s1", out: 4 })] }
    expect(lay(followPictures(BASE, moved, FPS).A1)).toBe("v2@0+2.5 v1@3+2 f@9+1")
  })

  it("Kürzen des Bildclips kürzt die Sprache mit (nie länger als ihr Bild)", () => {
    const cut: Tracks = { ...BASE, V1: [c({ id: "p1", shot_id: "s1", out: 1.5 }), c({ id: "p2", start: 1.5, shot_id: "s2", out: 3 })] }
    const a1 = followPictures(BASE, cut, FPS).A1
    expect(lay(a1)).toBe("v1@0+1.5 v2@1.5+2.5 f@9+1")
  })

  it("Anfang des Bildclips kürzen: Sprache bleibt am (neuen) Bildanfang", () => {
    const trimmed: Tracks = { ...BASE, V1: [c({ id: "p1", shot_id: "s1", in: 1, out: 4 }), c({ id: "p2", start: 3, shot_id: "s2", out: 3 })] }
    expect(lay(followPictures(BASE, trimmed, FPS).A1)).toBe("v1@0+2 v2@3+2.5 f@9+1")
  })

  it("Bildclip gelöscht: gebundene Sprache verschwindet mit", () => {
    const gone: Tracks = { ...BASE, V1: [c({ id: "p2", start: 0, shot_id: "s2", out: 3 })] }
    expect(lay(followPictures(BASE, gone, FPS).A1)).toBe("v2@0+2.5 f@9+1")
  })

  it("geteilter Bildclip: Sprache bleibt am ersten Teil", () => {
    const split: Tracks = { ...BASE, V1: [c({ id: "p1", shot_id: "s1", out: 1 }), c({ id: "p1b", start: 1, shot_id: "s1", in: 1, out: 4 }), c({ id: "p2", start: 4, shot_id: "s2", out: 3 })] }
    expect(lay(followPictures(BASE, split, FPS).A1)).toBe("v1@0+1 v2@4+2.5 f@9+1")
  })

  it("unverändert → dieselben Spuren zurück; freier Clip stößt an → rückt an die nächste freie Stelle", () => {
    expect(followPictures(BASE, BASE, FPS)).toBe(BASE)
    const crowd: Tracks = { ...BASE, A1: [...BASE.A1.slice(0, 2), v({ id: "f", start: 0.5, out: 1 })] }   // freier Clip im Weg
    const moved: Tracks = { ...crowd, V1: [c({ id: "p2", start: 0, shot_id: "s2", out: 3 }), c({ id: "p1", start: 3, shot_id: "s1", out: 4 })] }
    const a1 = followPictures(crowd, moved, FPS).A1
    expect(a1.find((x) => x.id === "v2")?.start).toBe(0)
    const f = a1.find((x) => x.id === "f")!
    expect(f.start).toBeGreaterThanOrEqual(2.5)                            // nicht über der gebundenen Sprache
  })

  it("Vom Shot lösen: Clip bleibt, ist danach frei", () => {
    const free = unbind(BASE, "v1")
    expect(free.A1.find((x) => x.id === "v1")?.shot_id).toBe("")
    expect(unbind(BASE, "weg")).toBe(BASE)
    // p1 nach hinten (Lücke vorn): gelöst → v1 bleibt bei 0, die gebundene v2 wandert mit p2
    const moved: Tracks = { ...free, V1: [c({ id: "p1", start: 10, shot_id: "s1", out: 4 }), c({ id: "p2", start: 4, shot_id: "s2", out: 3 })] }
    const a1 = followPictures(free, moved, FPS).A1
    expect(a1.find((x) => x.id === "v1")?.start).toBe(0)
    expect(a1.find((x) => x.id === "v2")?.start).toBe(4)
  })
})

describe("5c – Kürzen per Griff zieht die Sprache mit (wie im Hook)", () => {
  it("trimTracks: Bild kürzer → gebundene Sprache kürzer und rückt mit", async () => {
    const { trimTracks } = await import("./cutTracks")
    const a1 = trimTracks(BASE, "p1", "end", -2.48, FPS, {}).A1          // p1: 4 s → 1,52 s (bildgenau), p2 rückt nach
    expect(lay(a1)).toBe("v1@0+1.52 v2@1.52+2.5 f@9+1")
  })
})

describe("5c – jede Bearbeitung auf V1 nimmt die Sprache mit", () => {
  const ctx = { selected: "p1", time: 1, fps: FPS, newId: () => "n" }
  it("Löschen, Umsortieren, Bibliothek einfügen", async () => {
    const { addMedia, editTracks, moveVideoClip } = await import("./cutTracks")
    expect(lay(editTracks(BASE, { kind: "delete" }, ctx).A1)).toBe("v2@0+2.5 f@9+1")
    expect(lay(moveVideoClip(BASE, "p2", 0, FPS).A1)).toBe("v2@0+2.5 v1@3+2 f@9+1")
    const r = addMedia(BASE, { kind: "image", rel: "b.png", name: "B" }, { index: 0, time: 0 }, FPS, () => "neu")!
    expect(lay(r.tracks.A1)).toBe("v1@5+2 f@8+1 v2@9+2.5")               // Bild vorn: beide rücken 5 s, f weicht in die nächste Lücke
  })
})
