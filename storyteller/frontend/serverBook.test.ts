import { describe, expect, it } from "vitest"
import type { ServerFull } from "./api"
import { allScenes, updateScene } from "./model"
import { fromServer, headPatch, scenePatches, structureChanged, structureProblem, toImport, toStructure } from "./serverBook"

const full = (): ServerFull => ({
  book: { id: "b", title: "T", kind: "novel", language: "de", audience: "A", idea: "I", notes: "N", model: "m/x",
    ghost: { model: "g/m", length_words: 1500, chunk_words: 0, style: "" }, version: 3, created_at: "", updated_at: "2026-10-06" },
  structure: {
    version: 7,
    entities: [{ id: "e", kind: "character", name: "Gregor", aliases: ["Samsa"], description: "", fields: [{ key: "Beruf", value: "Reisender" }] }],
    parts: [{ id: "p", title: "Teil", chapters: [{ id: "c1", title: "K1", scenes: ["s2", "s1"] }, { id: "c2", title: "K2", scenes: ["s3"] }] }],
  },
  scenes: {
    s1: { id: "s1", title: "Eins", summary: "", pov: "", status: "draft", origin: "human", text: "a", version: 2, updated_at: "" },
    s2: { id: "s2", title: "Zwei", summary: "", pov: "", status: "idea", origin: "human", text: "b", version: 5, updated_at: "" },
    s3: { id: "s3", title: "Drei", summary: "", pov: "", status: "done", origin: "ai_draft", text: "c", version: 1, updated_at: "" },
  },
})

describe("serverBook", () => {
  it("baut das Buch in der Reihenfolge der Struktur und merkt sich alle Versionen", () => {
    const { book, versions } = fromServer(full())
    expect(allScenes(book).map((x) => x.scene.id)).toEqual(["s2", "s1", "s3"])
    expect(versions).toEqual({ book: 3, structure: 7, scenes: { s1: 2, s2: 5, s3: 1 } })
    expect(book.model).toBe("m/x")
  })
  it("Hin und zurück ergibt dieselbe Struktur", () => {
    const f = full()
    const { version: _v, ...st } = f.structure
    expect(toStructure(fromServer(f).book)).toEqual(st)
  })
  it("erkennt genau, was sich geändert hat", () => {
    const { book } = fromServer(full())
    const edited = { ...book, notes: "neu", parts: book.parts.map((p) => ({ ...p, chapters: p.chapters.map((c) => ({ ...c, scenes: c.scenes.map((s) => (s.id === "s1" ? { ...s, text: "x", status: "done" as const } : s)) })) })) }
    expect(headPatch(edited, book)).toEqual({ notes: "neu" })
    expect(scenePatches(edited, book)).toEqual([{ id: "s1", patch: { status: "done", text: "x" } }])
    expect(structureChanged(edited, book)).toBe(false)
    expect(structureChanged({ ...book, entities: [] }, book)).toBe(true)
  })
  it("Steckbrief ohne Namen kann nicht gespeichert werden", () => {
    const { book } = fromServer(full())
    expect(structureProblem(book)).toBe("")
    expect(structureProblem({ ...book, entities: [{ ...book.entities[0], name: " " }] })).toBe("entity_name_required")
  })
  it("Import-Form enthält Texte und Steckbriefe, aber keine IDs", () => {
    const imp = toImport(fromServer(full()).book)
    expect(imp.parts[0].chapters[0].scenes.map((s) => s.text)).toEqual(["b", "a"])
    expect(JSON.stringify(imp)).not.toMatch(/"id"/)
    expect(imp.entities[0]).toEqual({ kind: "character", name: "Gregor", aliases: ["Samsa"], description: "", fields: [{ key: "Beruf", value: "Reisender" }] })
  })
})

describe("serverBook – Ghostwriter-Einstellungen und Herkunft", () => {
  it("übernimmt ghost und origin; ältere Antworten ohne Felder bekommen Standardwerte", () => {
    const { book } = fromServer(full())
    expect(book.ghost).toEqual({ model: "g/m", length_words: 1500, chunk_words: 0, style: "" })
    expect(allScenes(book).find((x) => x.scene.id === "s3")?.scene.origin).toBe("ai_draft")
    const f = full()
    delete (f.book as Partial<typeof f.book>).ghost
    delete (f.scenes.s1 as Partial<typeof f.scenes.s1>).origin
    const old = fromServer(f).book
    expect(old.ghost.model).toBe("")
    expect(allScenes(old).find((x) => x.scene.id === "s1")?.scene.origin).toBe("human")
  })
  it("ghost-Änderung geht als Teil-Patch in den Kopf, origin als Szenenfeld", () => {
    const { book } = fromServer(full())
    const edited = { ...book, ghost: { ...book.ghost, style: "knapp" } }
    expect(headPatch(edited, book)).toEqual({ ghost: { style: "knapp" } })
    const s = updateScene(book, "s1", { text: "neu", origin: "ai_draft" })
    expect(scenePatches(s, book)).toEqual([{ id: "s1", patch: { origin: "ai_draft", text: "neu" } }])
  })
})
