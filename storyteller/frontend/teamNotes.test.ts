// T1d: Hinweise/Notizen des Teams – Filter (Szene/Kapitel/Buch), sichere Quellen-Links, Zählung je Szene.
import { describe, expect, it } from "vitest"
import { countByScene, filterNotes, safeUrl, type TeamNote } from "./teamNotes"

const n = (id: string, over: Partial<TeamNote> = {}): TeamNote => ({
  id, kind: "hint", title: id, text: "t", sources: [], author: "P", status: "open", at: "", seq: 1, ...over,
})
const chapters = { k1: ["s1", "s2"], k2: ["s3"] }

describe("teamNotes", () => {
  const list = [n("a", { scene_id: "s1" }), n("b", { scene_id: "s3" }), n("c", { chapter_id: "k1" }), n("d"),
    n("e", { entity_id: "x" })]
  it("Szene: nur Einträge dieser Szene", () => {
    expect(filterNotes(list, "scene", "s1", chapters).map((x) => x.id)).toEqual(["a"])
  })
  it("Kapitel: Einträge am Kapitel und an seinen Szenen", () => {
    expect(filterNotes(list, "chapter", "s1", chapters).map((x) => x.id)).toEqual(["a", "c"])
    expect(filterNotes(list, "chapter", "s3", chapters).map((x) => x.id)).toEqual(["b"])
  })
  it("Buch: alle", () => {
    expect(filterNotes(list, "book", "s1", chapters).map((x) => x.id)).toEqual(["a", "b", "c", "d", "e"])
  })
  it("zählt offene Einträge je Szene", () => {
    expect(countByScene([n("a", { scene_id: "s1" }), n("b", { scene_id: "s1" }), n("c", { scene_id: "s2", status: "done" }), n("d")]))
      .toEqual({ s1: 2 })
  })
  it("Links nur für http(s), sonst nichts", () => {
    expect(safeUrl("https://example.org/x")).toBe("https://example.org/x")
    expect(safeUrl("http://example.org")).toBe("http://example.org/")
    expect(safeUrl("javascript:alert(1)")).toBeNull()
    expect(safeUrl("data:text/html,x")).toBeNull()
    expect(safeUrl("kein link")).toBeNull()
  })
})
