import { describe, expect, it } from "vitest"
import { blankBook, defaultNames, groupLabelKey, isFiction } from "./bookFactory"
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
  it("Standardnamen folgen Buchart und Buchsprache", () => {
    expect(defaultNames("nonfiction", "de").scene(2)).toBe("Abschnitt 2")
    expect(defaultNames("novel", "de").chapter(3)).toBe("Kapitel 3")
    expect(defaultNames("novel", "en").scene(1)).toBe("Scene 1")
    expect(defaultNames("learning", "en-GB").scene(4)).toBe("Section 4")
    const b = blankBook({ title: "X", kind: "story", language: "en", audience: "", idea: "" })
    expect([b.parts[0].title, b.parts[0].chapters[0].title]).toEqual(["Part 1", "Chapter 1"])
  })
})
