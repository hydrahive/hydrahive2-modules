import { describe, expect, it } from "vitest"
import {
  addChapter, addScene, bookWords, countWords, entitiesInText, findScene, moveScene, nudgeScene,
  removeScene, renameNode, updateScene, type Book, type Scene,
} from "./model"

const sc = (id: string, text = ""): Scene => ({ id, title: id, summary: "", pov: "", status: "draft", text })
const book = (): Book => ({
  id: "b", title: "T", kind: "novel", language: "de", audience: "", idea: "", notes: "", updatedAt: "",
  parts: [{
    id: "p1", title: "Teil 1", chapters: [
      { id: "c1", title: "Kap 1", scenes: [sc("a", "Eins zwei drei."), sc("b"), sc("c")] },
      { id: "c2", title: "Kap 2", scenes: [sc("d", "vier")] },
    ],
  }],
  entities: [
    { id: "e1", kind: "character", name: "Gregor", aliases: ["Gregor Samsa"], description: "", fields: [] },
    { id: "e2", kind: "character", name: "Grete", aliases: [], description: "", fields: [] },
    { id: "e3", kind: "place", name: "Zimmer", aliases: [], description: "", fields: [] },
  ],
})
const order = (b: Book, c: number) => b.parts[0].chapters[c].scenes.map((s) => s.id).join("")

describe("Wörter", () => {
  it("zählt Wörter, Markdown-Zeichen und Satzzeichen zählen nicht", () => {
    expect(countWords("")).toBe(0)
    expect(countWords("## Titel\n\n**Fett** und *kursiv* – Ende.")).toBe(5)
    expect(countWords("> Zitat\n\n- eins\n- zwei")).toBe(3)
    expect(bookWords(book())).toBe(4)
  })
})

describe("Szenen verschieben", () => {
  it("innerhalb des Kapitels vor eine andere Szene", () => {
    expect(order(moveScene(book(), "c", "c1", "a"), 0)).toBe("cab")
  })
  it("in ein anderes Kapitel, ans Ende oder vor eine Szene", () => {
    const b1 = moveScene(book(), "a", "c2")
    expect(order(b1, 0)).toBe("bc")
    expect(order(b1, 1)).toBe("da")
    expect(order(moveScene(book(), "b", "c2", "d"), 1)).toBe("bd")
  })
  it("unbekannte Ziele oder vor sich selbst: unverändert", () => {
    const b = book()
    expect(moveScene(b, "a", "c9")).toBe(b)
    expect(moveScene(b, "a", "c1", "a")).toBe(b)
    expect(moveScene(b, "x", "c1")).toBe(b)
    expect(moveScene(b, "a", "c1", "d")).toBe(b)
  })
  it("Alt+↑/↓ verschiebt um eine Position, an den Rändern nichts", () => {
    expect(order(nudgeScene(book(), "b", -1), 0)).toBe("bac")
    expect(order(nudgeScene(book(), "b", 1), 0)).toBe("acb")
    const b = book()
    expect(nudgeScene(b, "a", -1)).toBe(b)
    expect(nudgeScene(b, "c", 1)).toBe(b)
  })
  it("das Original bleibt unverändert (keine versteckten Nebenwirkungen)", () => {
    const b = book()
    moveScene(b, "c", "c1", "a")
    expect(order(b, 0)).toBe("abc")
  })
})

describe("Anlegen, Umbenennen, Löschen", () => {
  it("neue Szene hinter einer bestimmten Szene, sonst am Ende", () => {
    const r1 = addScene(book(), "c1", "a")
    expect(r1.book.parts[0].chapters[0].scenes[1].id).toBe(r1.id)
    const r2 = addScene(book(), "c2")
    expect(r2.book.parts[0].chapters[1].scenes.at(-1)?.id).toBe(r2.id)
  })
  it("neues Kapitel bringt eine leere Szene mit", () => {
    const r = addChapter(book(), "p1")
    expect(r.book.parts[0].chapters).toHaveLength(3)
    expect(findScene(r.book, r.sceneId)?.chapter.title).toBe("Neues Kapitel")
  })
  it("leerer Name wird ignoriert, sonst umbenannt (Teil, Kapitel, Szene)", () => {
    const b = book()
    expect(renameNode(b, "c1", "   ")).toBe(b)
    const r = renameNode(renameNode(renameNode(b, "c1", " Anfang "), "a", "Erwachen"), "p1", "Erster Teil")
    expect(r.parts[0].title).toBe("Erster Teil")
    expect(r.parts[0].chapters[0].title).toBe("Anfang")
    expect(findScene(r, "a")?.scene.title).toBe("Erwachen")
  })
  it("die letzte Szene eines Kapitels lässt sich nicht löschen", () => {
    const b = book()
    expect(removeScene(b, "d")).toBe(b)
    expect(order(removeScene(b, "b"), 0)).toBe("ac")
  })
  it("updateScene ändert nur die Ziel-Szene und nie die ID", () => {
    const r = updateScene(book(), "b", { text: "neu", id: "hack" } as Partial<Scene>)
    expect(findScene(r, "b")?.scene.text).toBe("neu")
    expect(findScene(r, "hack")).toBeNull()
  })
})

describe("Steckbriefe im Text", () => {
  it("findet Namen und Spitznamen als ganze Wörter, Groß/klein egal", () => {
    const e = book().entities
    expect(entitiesInText(e, "gregor stand auf.").map((x) => x.id)).toEqual(["e1"])
    expect(entitiesInText(e, "Gregors Zimmer").map((x) => x.id)).toEqual(["e3"])
    expect(entitiesInText(e, "Grete und Gregor Samsa").map((x) => x.id).sort()).toEqual(["e1", "e2"])
    expect(entitiesInText(e, "Nichts davon.")).toEqual([])
  })
})
