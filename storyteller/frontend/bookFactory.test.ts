import { describe, expect, it } from "vitest"
import { defaultNames, groupLabelKey, isFiction } from "./bookFactory"

describe("bookFactory", () => {
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
    expect([defaultNames("story", "en").part, defaultNames("story", "en").chapter(1)]).toEqual(["Part 1", "Chapter 1"])
    expect(defaultNames("nonfiction", "de").part).toBe("Inhalt")
  })
})
