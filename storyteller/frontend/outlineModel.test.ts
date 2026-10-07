// Gliederung aus Idee (Ghostwriter G2) bearbeiten, bevor sie übernommen wird – ohne React.
import { describe, expect, it } from "vitest"
import { editScene, outlineProblem, outlineStats, removeChapter, removeScene, renameChapter, type Outline } from "./outlineModel"

const o = (): Outline => ({
  chapters: [
    { title: "Ankunft", scenes: [{ title: "Bahnhof", summary: "Mia kommt an.", pov: "Mia" }, { title: "Haus", summary: "Leer.", pov: "" }] },
    { title: "Spuren", scenes: [{ title: "Brief", summary: "Ein Brief.", pov: "" }] },
  ],
  entities: [{ name: "Mia", kind: "character", description: "Zwölf." }],
})

describe("outlineModel", () => {
  it("Szene ändern ist unveränderlich (Kopie)", () => {
    const a = o()
    const b = editScene(a, 0, 1, { summary: "Das Haus ist verlassen." })
    expect(b.chapters[0].scenes[1].summary).toBe("Das Haus ist verlassen.")
    expect(a.chapters[0].scenes[1].summary).toBe("Leer.")
  })
  it("Szene streichen; letzte Szene streicht das Kapitel", () => {
    const b = removeScene(o(), 0, 0)
    expect(b.chapters[0].scenes.map((s) => s.title)).toEqual(["Haus"])
    const c = removeScene(o(), 1, 0)
    expect(c.chapters.map((x) => x.title)).toEqual(["Ankunft"])
  })
  it("Kapitel umbenennen und streichen", () => {
    expect(renameChapter(o(), 1, "Hinweise").chapters[1].title).toBe("Hinweise")
    expect(removeChapter(o(), 0).chapters.map((x) => x.title)).toEqual(["Spuren"])
  })
  it("Zählt Kapitel und Szenen", () => {
    expect(outlineStats(o())).toEqual({ chapters: 2, scenes: 3 })
  })
  it("meldet Probleme vor dem Übernehmen", () => {
    expect(outlineProblem(o())).toBeNull()
    expect(outlineProblem({ ...o(), chapters: [] })).toBe("outline_empty")
    expect(outlineProblem(renameChapter(o(), 0, "  "))).toBe("outline_title_missing")
    expect(outlineProblem(editScene(o(), 0, 0, { title: "" }))).toBe("outline_title_missing")
    expect(outlineProblem(editScene(o(), 0, 0, { summary: " " }))).toBe("outline_summary_missing")
  })
})
