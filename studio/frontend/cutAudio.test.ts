import { describe, expect, it } from "vitest"
import { audioAt, audioTrackFor, dropAudio, fromLibraryAudio, moveAudio, placeFree, splitAudio, splitKeepAudio, trimAudio } from "./cutAudio"
import type { TimelineClip } from "./timelineApi"

const FPS = 25
let n = 0
const id = () => `n${++n}`
const a = (p: Partial<TimelineClip>): TimelineClip => ({ id: "x", kind: "audio", start: 0, in: 0, out: 5, media_rel: "atelier/audio/m.mp3",
  scene_id: "", shot_id: "", label: "M", ...p })
const lay = (cs: TimelineClip[]) => [...cs].sort((x, y) => x.start - y.start).map((x) => `${x.id}@${x.start}+${Math.round((x.out - x.in) * 100) / 100}`).join(" ")
const M1 = a({ id: "m1", start: 0, out: 4 })              // 0–4
const M2 = a({ id: "m2", start: 10, out: 3 })             // 10–13

describe("5a – Tonspuren: frei, Lücken bleiben, nie überlappend", () => {
  it("Musik kommt auf „Musik“, alles andere Hörbare auf „Sprache“", () => {
    expect(audioTrackFor("music")).toBe("A2")
    expect(audioTrackFor("audio")).toBe("A1")
    expect(audioTrackFor("image")).toBeNull()
    expect(audioTrackFor("element")).toBeNull()
  })

  it("Bibliothekseintrag → Tonclip (Länge aus der Bibliothek, sonst 10 s)", () => {
    expect(fromLibraryAudio({ kind: "music", rel: "tonstudio/clips/a.mp3", name: "Lied", duration: 30 }, 2, id))
      .toMatchObject({ kind: "audio", start: 2, in: 0, out: 30, media_rel: "tonstudio/clips/a.mp3", label: "Lied" })
    expect(fromLibraryAudio({ kind: "audio", rel: "x.wav", name: "S" }, 0, id)?.out).toBe(10)
    expect(fromLibraryAudio({ kind: "video", rel: "v.mp4", name: "V" }, 0, id)).toBeNull()
  })

  it("Platz suchen: gewünschte Stelle, sonst die nächste freie Lücke, in der der Clip ganz Platz hat", () => {
    expect(placeFree([M1, M2], 5, 3, FPS)).toBe(5)              // 5–8 frei
    expect(placeFree([M1, M2], 2, 3, FPS)).toBe(4)              // läge auf M1 → direkt dahinter
    expect(placeFree([M1, M2], 8, 3, FPS)).toBe(7)              // 8–11 stößt an M2 → davor, falls näher
    expect(placeFree([M1, M2], 9, 7, FPS)).toBe(13)             // Lücke 4–10 zu klein → hinter M2
    expect(placeFree([], -3, 2, FPS)).toBe(0)                   // nie vor 0
    expect(placeFree([M2], -3, 2, FPS)).toBe(0)                 // nie vor 0, auch mit anderen Clips
    expect(placeFree([], 1.013, 1, FPS)).toBe(1)                // bildgenau (1,013 s → Bild 25)
    expect(placeFree([M1], 1.013, 1, FPS)).toBe(4)
  })

  it("Ablegen aus der Bibliothek: an freier Stelle, Rest unverändert", () => {
    const c = fromLibraryAudio({ kind: "music", rel: "m.mp3", name: "N", duration: 3 }, 0, id)!
    expect(lay(dropAudio([M1, M2], c, 2, FPS))).toBe(`m1@0+4 ${c.id}@4+3 m2@10+3`)
  })

  it("Verschieben: freie Stelle, ohne sich selbst zu stören; Lücken der anderen bleiben", () => {
    expect(lay(moveAudio([M1, M2], "m1", 5, FPS))).toBe("m1@5+4 m2@10+3")
    expect(lay(moveAudio([M1, M2], "m1", 1, FPS))).toBe("m1@1+4 m2@10+3")      // überlappt nur sich selbst
    expect(lay(moveAudio([M1, M2], "m2", 2, FPS))).toBe("m1@0+4 m2@4+3")
    expect(moveAudio([M1, M2], "weg", 5, FPS)).toEqual([M1, M2])
  })

  it("Kürzen: Anfang verschiebt Start und Stelle im Medium gemeinsam; Ende nie über den Nachbarn oder das Medium hinaus", () => {
    expect(lay(trimAudio([M1, M2], "m1", "start", 1, FPS))).toBe("m1@1+3 m2@10+3")
    expect(trimAudio([M1, M2], "m1", "start", 1, FPS).find((c) => c.id === "m1")?.in).toBe(1)
    expect(lay(trimAudio([M1, M2], "m1", "start", -2, FPS))).toBe("m1@0+4 m2@10+3")       // in kann nicht < 0
    expect(lay(trimAudio([M1, M2], "m1", "end", 20, FPS))).toBe("m1@0+10 m2@10+3")        // stößt an M2
    expect(lay(trimAudio([M1, M2], "m1", "end", 20, FPS, { m1: 6 }))).toBe("m1@0+6 m2@10+3") // Medium nur 6 s lang
    expect(lay(trimAudio([M1, M2], "m2", "start", -20, FPS))).toBe("m1@0+4 m2@10+3")      // in = 0: früher geht es nicht
    const M3 = a({ id: "m3", start: 10, in: 8, out: 11 })
    expect(lay(trimAudio([M1, M3], "m3", "start", -20, FPS))).toBe("m1@0+4 m3@4+9")       // bis an M1, nicht darüber
    expect(Math.round((trimAudio([M1], "m1", "end", -10, FPS)[0].out - 0) * FPS)).toBe(5)  // Mindestlänge 5 Bilder
  })

  it("Teilen: Stelle im Medium läuft auch bei Ausschnitt weiter (in > 0)", () => {
    const cut = a({ id: "k", start: 10, in: 3, out: 9 })               // 10–16, Medium 3–9
    const s = splitAudio([cut], 12, FPS, id)
    expect(s.find((c) => c.start === 12)?.in).toBe(5)                  // 3 + (12 − 10)
    expect(s.find((c) => c.id === "k")?.out).toBe(5)
  })

  it("Teilen am Abspielkopf: zwei Teile, Stelle im Medium läuft weiter", () => {
    const s = splitAudio([M1, M2], 1.6, FPS, id)
    expect(lay(s)).toMatch(/^m1@0\+1\.6 n\d+@1\.6\+2\.4 m2@10\+3$/)
    expect(s.find((c) => c.start === 1.6)?.in).toBe(1.6)
    expect(splitAudio([M1, M2], 7, FPS, id)).toEqual([M1, M2])            // Lücke: nichts
    expect(splitAudio([M1], 0.1, FPS, id)).toEqual([M1])                   // zu nah am Rand
  })

  it("Abspielen: welcher Tonclip bei t (Start inklusive, Ende exklusiv)", () => {
    expect(audioAt([M1, M2], 0)?.id).toBe("m1")
    expect(audioAt([M1, M2], 4)).toBeNull()
    expect(audioAt([M2, M1], 12.9)?.id).toBe("m2")
    expect(audioAt([a({ id: "z", missing: true, media_rel: "" })], 1)).toBeNull()   // gelöschtes Medium = Stille
  })
})

describe("5a – Q/W auf der Tonspur", () => {
  it("teilt und entfernt links bzw. rechts, ohne etwas nachzuschieben", () => {
    expect(lay(splitKeepAudio([M1, M2], 2, "left", FPS, id))).toMatch(/^n\d+@2\+2 m2@10\+3$/)
    expect(lay(splitKeepAudio([M1, M2], 2, "right", FPS, id))).toBe("m1@0+2 m2@10+3")
    expect(splitKeepAudio([M1, M2], 7, "left", FPS, id)).toEqual([M1, M2])
  })
})

describe("5a – Ton in der Vorschau", () => {
  it("Soll-Stelle im Tonclip und wann nachgestellt wird", async () => {
    const { soundTarget, needsSeek } = await import("./soundLogic")
    const c = a({ id: "m", start: 2, in: 3, out: 8 })
    expect(soundTarget([c], 4)).toEqual({ clip: c, at: 5 })
    expect(soundTarget([c], 1)).toBeNull()
    expect(soundTarget([c], 7)).toBeNull()                                  // 2 + (8 − 3) = 7 → Ende exklusiv
    expect(needsSeek(5, 5.1, true)).toBe(false)
    expect(needsSeek(5, 5.2, true)).toBe(true)
    expect(needsSeek(5, 5.05, false)).toBe(true)
  })
})


describe("5a – Länge vor dem Ablegen messen", () => {
  it("nur bei Ton ohne bekannte Länge; gemessene Länge wird übernommen", async () => {
    const { needsLength, withLength } = await import("./cutAudio")
    expect(needsLength({ kind: "music" })).toBe(true)
    expect(needsLength({ kind: "audio", duration: 0 })).toBe(true)
    expect(needsLength({ kind: "music", duration: 3 })).toBe(false)
    expect(needsLength({ kind: "image" })).toBe(false)
    expect(needsLength({ kind: "video" })).toBe(false)
    expect(withLength<{ kind: string; duration?: number }>({ kind: "music" }, 3.03)).toEqual({ kind: "music", duration: 3.03 })
    const it0: { kind: string; duration?: number } = { kind: "music" }
    expect(withLength(it0, 0)).toBe(it0)
  })
})
