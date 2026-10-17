import { describe, expect, it } from "vitest"
import {
  append, duplicate, fromLibrary, insertAt, moveTo, pack, paste, remove, snapEdge, splitAt, splitKeep, trim, MIN_FRAMES,
} from "./cutEdit"
import { History } from "./cutHistory"
import type { TimelineClip } from "./timelineApi"

const FPS = 25
let n = 0
const id = () => `n${++n}`
const c = (p: Partial<TimelineClip>): TimelineClip => ({ id: "x", kind: "image", start: 0, in: 0, out: 5, media_rel: "studio/media/images/a.png",
  scene_id: "", shot_id: "", label: "x", ...p })
const A = c({ id: "a", out: 4 })                                                        // 0–4
const B = c({ id: "b", kind: "video", start: 4, in: 1, out: 7, media_rel: "studio/media/videos/b.mp4" })   // 4–10, Quelle 1–7
const C = c({ id: "c", kind: "placeholder", start: 10, out: 2, media_rel: "" })       // 10–12
const ALL = [A, B, C]
const lay = (cs: TimelineClip[]) => cs.map((x) => `${x.id}@${x.start}+${Math.round((x.out - x.in) * 100) / 100}`).join(" ")

describe("4b – magnetische Hauptspur", () => {
  it("pack: lückenlos, Reihenfolge bleibt, bildgenau, nie kürzer als die Mindestlänge", () => {
    expect(lay(pack([c({ id: "a", start: 3, out: 2 }), c({ id: "b", start: 9, in: 0.013, out: 1.01 })], FPS))).toBe("a@0+2 b@2+1")
    const tiny = pack([c({ id: "a", in: 1, out: 1.04 })], FPS)[0]                   // 1 Bild → auf 5 Bilder aufgefüllt
    expect(Math.round((tiny.out - tiny.in) * FPS)).toBe(MIN_FRAMES)
  })

  it("Umsortieren: an Anfang, Mitte, Ende; gleiche Stelle ändert nichts", () => {
    expect(lay(moveTo(ALL, "c", 0, FPS))).toBe("c@0+2 a@2+4 b@6+6")
    expect(lay(moveTo(ALL, "a", 1, FPS))).toBe("b@0+6 a@6+4 c@10+2")             // Index = Stelle in der Liste ohne den Clip
    expect(lay(moveTo(ALL, "a", 2, FPS))).toBe("b@0+6 c@6+2 a@8+4")
    expect(lay(moveTo(ALL, "a", 99, FPS))).toBe("b@0+6 c@6+2 a@8+4")
    expect(moveTo(ALL, "b", 1, FPS)).toBe(ALL)                                       // gleiche Stelle: unverändert, kein neuer Stand
    expect(moveTo(ALL, "gibt-es-nicht", 0, FPS)).toBe(ALL)
    expect(lay(moveTo(ALL, "c", -1, FPS))).toBe("c@0+2 a@2+4 b@6+6")             // Stelle vor dem Anfang → an den Anfang (nicht vom Ende gezählt)
  })

  it("Einfügemarke: Index aus der Zeit (vor/hinter der Mitte eines Clips)", () => {
    expect(insertAt(ALL, 1.9)).toBe(0)
    expect(insertAt(ALL, 2.1)).toBe(1)
    expect(insertAt(ALL, 6.9)).toBe(1)
    expect(insertAt(ALL, 7.1)).toBe(2)
    expect(insertAt(ALL, 50)).toBe(3)
    expect(insertAt([], 3)).toBe(0)
  })

  it("Teilen am Abspielkopf: zwei Clips, Quelle passt, Rest unverändert; am Rand oder in der Lücke nichts", () => {
    const r = splitAt(ALL, 6, FPS, id)
    expect(lay(r).replace(/n\d+/, "R")).toBe("a@0+4 b@4+2 R@6+4 c@10+2")
    expect(r[1]).toMatchObject({ id: "b", in: 1, out: 3 })
    expect(r[2]).toMatchObject({ kind: "video", in: 3, out: 7, media_rel: B.media_rel })
    expect(splitAt(ALL, 4, FPS, id)).toBe(ALL)                                     // genau an einer Grenze
    expect(splitAt([A], 0, FPS, id)).toHaveLength(1)                                // am Filmanfang
    expect(splitAt([A], 4, FPS, id)).toHaveLength(1)                                // am Filmende
    expect(splitAt(ALL, 4 + 2 / FPS, FPS, id)).toEqual(ALL)                       // Rest wäre kürzer als die Mindestlänge
    expect(splitAt(ALL, 20, FPS, id)).toEqual(ALL)
    expect(splitAt(ALL, 6.013, FPS, id)[1].out).toBe(3)                            // bildgenau gerundet
  })

  it("Teilen und links/rechts löschen (Q/W) – Rest rückt nach", () => {
    const q = splitKeep(ALL, 6, "left", FPS, id)                                     // Q: links vom Abspielkopf weg
    expect(lay(q).replace(/n\d+/, "R")).toBe("a@0+4 R@4+4 c@8+2")
    expect(q[1]).toMatchObject({ in: 3, out: 7 })
    expect(lay(splitKeep(ALL, 6, "right", FPS, id))).toBe("a@0+4 b@4+2 c@6+2")     // W: rechts weg
    expect(splitKeep(ALL, 50, "left", FPS, id)).toEqual(ALL)
  })

  it("Kürzen: Ränder, Mindestlänge, Video-Ende, Bilder frei verlängerbar; Rest rückt nach", () => {
    expect(lay(trim(ALL, "b", "end", -2, FPS))).toBe("a@0+4 b@4+4 c@8+2")
    expect(trim(ALL, "b", "start", 0.48, FPS)[1]).toMatchObject({ in: 1.48, out: 7, start: 4 })
    expect(trim(ALL, "b", "start", 0.5, FPS)[1].in).toBe(1.52)                     // 37,5 Bilder → 38 (bildgenau)
    expect(trim(ALL, "b", "start", -5, FPS)[1].in).toBe(0)                          // nicht vor den Anfang der Quelle
    expect(trim(ALL, "b", "end", 99, FPS, { b: 8 })[1].out).toBe(8)                 // nicht über das Video-Ende
    expect(trim(ALL, "b", "end", 99, FPS)[1].out).toBe(106)                         // Länge unbekannt → frei
    expect(trim(ALL, "a", "end", 3, FPS)[0].out).toBe(7)                            // Bild: frei verlängerbar
    const min = trim(ALL, "a", "end", -99, FPS)[0]
    expect(Math.round((min.out - min.in) * FPS)).toBe(MIN_FRAMES)
    expect(min.out).toBe(MIN_FRAMES / FPS)                                           // nicht erst beim Packen aufgefüllt
    const minStart = trim(ALL, "b", "start", 99, FPS)[1]
    expect(Math.round((minStart.out - minStart.in) * FPS)).toBe(MIN_FRAMES)
    expect(minStart).toMatchObject({ in: 7 - MIN_FRAMES / FPS, out: 7 })            // der Anfang wandert, das Ende bleibt
  })

  it("Kürzen in vielen kleinen Schritten = ein großer Schritt vom Ausgangsstand (nichts geht durch Runden verloren)", () => {
    // Die Oberfläche rechnet beim Ziehen immer vom Stand beim Greifen aus – so wie hier: Gesamtverschiebung je Ereignis.
    const total = -1.6
    let shown = ALL
    for (let i = 1; i <= 6; i++) shown = trim(ALL, "b", "end", (total * i) / 6, FPS)
    expect(shown[1].out).toBe(trim(ALL, "b", "end", total, FPS)[1].out)
    expect(shown[1].out).toBe(5.4)
    let wrong = ALL                                                                       // so war es falsch: kleine Schritte auf dem schon gekürzten Stand
    for (let i = 0; i < 6; i++) wrong = trim(wrong, "b", "end", total / 6 / 20, FPS)
    expect(wrong[1].out).toBe(7)                                                          // jeder Mini-Schritt fällt beim Runden weg
  })

  it("Löschen, Verdoppeln, Einfügen, Anhängen", () => {
    expect(lay(remove(ALL, "b", FPS))).toBe("a@0+4 c@4+2")
    const d = duplicate(ALL, "a", FPS, id)
    expect(lay(d).replace(/n\d+/, "N")).toBe("a@0+4 N@4+4 b@8+6 c@14+2")
    expect(d[1]).toMatchObject({ kind: "image", media_rel: A.media_rel, label: A.label })
    expect(lay(paste(ALL, C, "a", FPS, id)).replace(/n\d+/, "N")).toBe("a@0+4 N@4+2 b@6+6 c@12+2")
    expect(lay(paste(ALL, C, null, FPS, id)).replace(/n\d+/, "N")).toBe("a@0+4 b@4+6 c@10+2 N@12+2")
    expect(paste(ALL, { ...C, missing: true }, null, FPS, id)[3].missing).toBe(true)
    expect(lay(append(ALL, c({ id: "z", out: 1 }), 0, FPS))).toBe("z@0+1 a@1+4 b@5+6 c@11+2")
  })

  it("Aus der Bibliothek: Bild 5 s, Video volle Länge, sonst 5 s; Ton geht nicht", () => {
    const img = fromLibrary({ kind: "image", rel: "atelier/images/x.png", name: "Leuchtturm" }, id)
    expect(img).toMatchObject({ kind: "image", in: 0, out: 5, media_rel: "atelier/images/x.png", label: "Leuchtturm" })
    expect(fromLibrary({ kind: "video", rel: "v.mp4", name: "V", duration: 7.3 }, id)).toMatchObject({ kind: "video", out: 7.3 })
    expect(fromLibrary({ kind: "video", rel: "v.mp4", name: "V" }, id)?.out).toBe(5)
    expect(fromLibrary({ kind: "music", rel: "m.mp3", name: "M" }, id)).toBeNull()
    expect(fromLibrary({ kind: "element", rel: "", name: "Ole" }, id)).toBeNull()
  })

  it("Einrasten: Rand rastet am Abspielkopf ein, wenn nah genug (in Pixeln)", () => {
    expect(snapEdge(5.05, [5], 10, 100)).toBe(5)                                   // 0,05 s = 0,5 px bei 10 s / 100 px
    expect(snapEdge(5.05, [5], 10, 1000)).toBe(5)                                  // 5 px – noch drin
    expect(snapEdge(5.2, [5], 10, 1000)).toBe(5.2)                                 // 20 px – zu weit
    expect(snapEdge(3, [], 10, 1000)).toBe(3)
  })
})

describe("4b – Rückgängig / Wiederholen", () => {
  it("Schritte zurück und vor, neue Änderung löscht das Wiederholen, höchstens 100", () => {
    const h = new History<number>(0)
    h.push(1); h.push(2); h.push(3)
    expect(h.undo()).toBe(2)
    expect(h.undo()).toBe(1)
    expect(h.redo()).toBe(2)
    h.push(9)
    expect(h.canRedo).toBe(false)
    expect(h.undo()).toBe(2)
    expect(h.undo()).toBe(1)
    expect(h.undo()).toBe(0)
    expect(h.canUndo).toBe(false)
    expect(h.undo()).toBe(0)                                                        // am Anfang bleibt es
    const big = new History<number>(0)
    for (let i = 1; i <= 150; i++) big.push(i)
    let steps = 0
    while (big.canUndo) { big.undo(); steps++ }
    expect(steps).toBe(100)
    expect(big.current).toBe(50)
    h.reset(7)
    expect([h.current, h.canUndo, h.canRedo]).toEqual([7, false, false])
  })
})
