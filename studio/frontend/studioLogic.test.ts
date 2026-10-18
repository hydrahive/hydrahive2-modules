import { describe, expect, it } from "vitest"
import { DEFAULT_LAYOUT, STORAGE_KEY, clampLayout, dragLayout, loadLayout, saveLayout } from "./layout"
import { SHORTCUTS, actionFor, keyLabel, keyName } from "./shortcuts"
import { centerAt, clampViewport, timecode, tickStep, toFraction, zoom } from "./timeline"

const key = (k: string, mods: Partial<{ ctrlKey: boolean; metaKey: boolean; shiftKey: boolean; altKey: boolean }> = {}) =>
  ({ key: k, ctrlKey: false, metaKey: false, shiftKey: false, altKey: false, ...mods })

describe("Tastenkürzel", () => {
  it("Standard-Kürzel wie in Schnittprogrammen", () => {
    expect(actionFor(key(" "), null)).toBe("toggle-play")
    expect(actionFor(key("k"), null)).toBe("toggle-play")
    expect(actionFor(key("j"), null)).toBe("seek-back")
    expect(actionFor(key("l"), null)).toBe("seek-forward")
    expect(actionFor(key("S"), null)).toBe("split")
    expect(actionFor(key("ArrowLeft", { shiftKey: true }), null)).toBe("jump-back")
    expect(actionFor(key("z", { ctrlKey: true }), null)).toBe("undo")
    expect(actionFor(key("z", { ctrlKey: true, shiftKey: true }), null)).toBe("redo")
    expect(actionFor(key("k", { metaKey: true }), null)).toBe("command")
    expect(actionFor(key("?", { shiftKey: true }), null)).toBe("help")
  })

  it("wirkt nicht in Eingabefeldern", () => {
    for (const tagName of ["INPUT", "TEXTAREA", "SELECT"]) {
      expect(actionFor(key("s"), { tagName } as unknown as EventTarget)).toBeNull()
    }
    expect(actionFor(key("s"), { tagName: "DIV", isContentEditable: true } as unknown as EventTarget)).toBeNull()
    expect(actionFor(key("s"), { tagName: "DIV" } as unknown as EventTarget)).toBe("split")
  })

  it("Regler und Kästchen (5b): Kürzel wirken, nur Pfeile/Pos1/Ende und Leertaste gehören dem Element", () => {
    const range = { tagName: "INPUT", type: "range" } as unknown as EventTarget
    const box = { tagName: "INPUT", type: "checkbox" } as unknown as EventTarget
    expect(actionFor(key("z", { ctrlKey: true }), range)).toBe("undo")
    expect(actionFor(key("z", { ctrlKey: true, shiftKey: true }), range)).toBe("redo")
    expect(actionFor(key("k"), range)).toBe("toggle-play")
    expect(actionFor(key("s"), range)).toBe("split")
    for (const k of ["ArrowLeft", "ArrowRight", "Home", "End"]) expect(actionFor(key(k), range)).toBeNull()
    expect(actionFor(key(" "), box)).toBeNull()                                  // Leertaste schaltet das Kästchen
    expect(actionFor(key("z", { ctrlKey: true }), box)).toBe("undo")
    expect(actionFor(key("z", { ctrlKey: true }), { tagName: "INPUT", type: "number" } as unknown as EventTarget)).toBeNull()
  })

  it("jede Taste nur einmal vergeben, Anzeige lesbar", () => {
    const all = SHORTCUTS.flatMap((s) => s.keys)
    expect(new Set(all).size).toBe(all.length)
    expect(keyName(key("Z", { ctrlKey: true, shiftKey: true }))).toBe("ctrl+shift+z")
    expect(keyLabel("ctrl+shift+z")).toBe("Strg + Shift + Z")
    expect(keyLabel("space")).toBe("Leertaste")
  })
})

describe("Panel-Aufteilung", () => {
  it("Grenzen werden eingehalten, Unsinn fällt auf Standard zurück", () => {
    expect(clampLayout({ library: 99, inspector: 1, timeline: "x" })).toEqual({ library: 35, inspector: 14, timeline: DEFAULT_LAYOUT.timeline })
    expect(clampLayout(null)).toEqual(DEFAULT_LAYOUT)
  })

  it("Ziehen: Bibliothek nach rechts größer, Eigenschaften und Zeitleiste nach links/oben größer", () => {
    expect(dragLayout(DEFAULT_LAYOUT, "library", 5).library).toBe(25)
    expect(dragLayout(DEFAULT_LAYOUT, "inspector", -5).inspector).toBe(27)
    expect(dragLayout(DEFAULT_LAYOUT, "timeline", -10).timeline).toBe(50)
  })

  it("wird gespeichert und wieder geladen, kaputte Daten schaden nicht", () => {
    const store: Record<string, string> = {}
    const storage = { getItem: (k: string) => store[k] ?? null, setItem: (k: string, v: string) => { store[k] = v } }
    saveLayout({ library: 30, inspector: 20, timeline: 55 }, storage)
    expect(loadLayout(storage)).toEqual({ library: 30, inspector: 20, timeline: 55 })
    store[STORAGE_KEY] = "{kaputt"
    expect(loadLayout(storage)).toEqual(DEFAULT_LAYOUT)
  })
})

describe("Zeitleiste", () => {
  it("Ausschnitt bleibt im Film, Zoom um den Anker", () => {
    expect(clampViewport({ start: -5, span: 200 }, 90)).toEqual({ start: 0, span: 90 })
    const z = zoom({ start: 0, span: 40 }, 0.5, 0.5, 90)
    expect(z).toEqual({ start: 10, span: 20 })
    expect(toFraction(20, z)).toBe(0.5)
  })

  it("Übersichtsleiste zentriert den Ausschnitt, auch am Rand", () => {
    expect(centerAt({ start: 0, span: 20 }, 0.5, 90)).toEqual({ start: 35, span: 20 })
    expect(centerAt({ start: 0, span: 20 }, 1, 90)).toEqual({ start: 70, span: 20 })
  })

  it("Zeitcode und Zeitmarken", () => {
    expect(timecode(12.16)).toBe("00:00:12:04")
    expect(timecode(3725)).toBe("01:02:05:00")
    expect(tickStep(90)).toBe(10)
    expect(tickStep(8)).toBe(1)
  })
})
