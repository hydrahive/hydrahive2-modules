import { describe, expect, it } from "vitest"
import type { LibraryItem } from "./api"
import { formatSize, grouped, pickProject, previewMode, visible } from "./libraryView"

const item = (p: Partial<LibraryItem>): LibraryItem => ({
  id: "x", kind: "image", origin: "ai", source: "atelier", name: "x", rel: "atelier/images/x.png",
  abs: "/w/atelier/images/x.png", size: 1, created_at: "2026-10-15T00:00:00Z", ...p,
})

const ITEMS = [
  item({ id: "1", kind: "video", name: "Mira am Steg", prompt: "Hafen im Sturm" }),
  item({ id: "2", kind: "image", name: "Titelbild" }),
  item({ id: "3", kind: "music", name: "Nordwind", source: "tonstudio" }),
  item({ id: "4", kind: "video", name: "Drohne", origin: "upload", source: "videoeditor" }),
  item({ id: "5", kind: "element", name: "Mira" }),
]

describe("Bibliothek", () => {
  it("filtert nach Art, sucht in Name und Beschreibung", () => {
    expect(visible(ITEMS, "video", "").map((i) => i.id)).toEqual(["1", "4"])
    expect(visible(ITEMS, "all", "sturm").map((i) => i.id)).toEqual(["1"])
    expect(visible(ITEMS, "all", "  MIRA ").map((i) => i.id)).toEqual(["1", "5"])
    expect(visible(ITEMS, "music", "").map((i) => i.id)).toEqual(["3"])
  })

  it("Ordner: KI-erzeugt vor Hochgeladen, leere Ordner fehlen", () => {
    expect(grouped(ITEMS).map((g) => [g.group, g.items.map((i) => i.id)])).toEqual([["ai", ["1", "2", "3", "5"]], ["upload", ["4"]]])
    expect(grouped([ITEMS[3]]).map((g) => g.group)).toEqual(["upload"])
  })

  it("merkt das Projekt, nimmt das erste, wenn das gemerkte weg ist", () => {
    const ps = [{ id: "a", name: "A" }, { id: "b", name: "B" }]
    expect(pickProject(ps, "b")).toBe("b")
    expect(pickProject(ps, "weg")).toBe("a")
    expect(pickProject([], "b")).toBe("")
  })

  it("Vorschau je Art, Größen lesbar", () => {
    expect(ITEMS.map((i) => previewMode(i))).toEqual(["video", "image", "audio", "video", "element"])
    expect(previewMode(null)).toBe("none")
    expect(formatSize(512)).toBe("512 B")
    expect(formatSize(67205831)).toBe("64.1 MB")
  })
})
