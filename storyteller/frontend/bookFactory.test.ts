import { describe, expect, it } from "vitest"
import { blankBook, groupLabelKey, isFiction } from "./bookFactory"
import { allScenes } from "./model"

describe("bookFactory", () => {
  it("Roman: Vorlage Teil 1 → Kapitel 1 → Szene 1, Titel getrimmt", () => {
    const b = blankBook({ title: "  Der Leuchtturm ", kind: "novel", language: "de", audience: "", idea: "" })
    expect(b.title).toBe("Der Leuchtturm")
    expect(allScenes(b).map((x) => [x.chapter.title, x.scene.title])).toEqual([["Kapitel 1", "Szene 1"]])
  })
  it("Sachbuch: „Abschnitt“ statt „Szene“", () => {
    const b = blankBook({ title: "X", kind: "nonfiction", language: "de", audience: "", idea: "" })
    expect(allScenes(b)[0].scene.title).toBe("Abschnitt 1")
  })
  it("Gruppen heißen bei Sach-/Lernbuch Personen/Begriffe/Quellen", () => {
    expect(isFiction("story")).toBe(true)
    expect(groupLabelKey("novel", "place")).toBe("group_place")
    expect(groupLabelKey("learning", "character")).toBe("group_person")
    expect(groupLabelKey("nonfiction", "item")).toBe("group_source")
  })
})
