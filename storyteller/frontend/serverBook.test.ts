import { describe, expect, it } from "vitest"
import type { ServerFull } from "./api"
import { allScenes } from "./model"
import { fromServer, headPatch, scenePatches, structureChanged, structureProblem, toImport, toStructure } from "./serverBook"

const full = (): ServerFull => ({
  book: { id: "b", title: "T", kind: "novel", language: "de", audience: "A", idea: "I", notes: "N", model: "m/x", version: 3, created_at: "", updated_at: "2026-10-06" },
  structure: {
    version: 7,
    entities: [{ id: "e", kind: "character", name: "Gregor", aliases: ["Samsa"], description: "", fields: [{ key: "Beruf", value: "Reisender" }] }],
    parts: [{ id: "p", title: "Teil", chapters: [{ id: "c1", title: "K1", scenes: ["s2", "s1"] }, { id: "c2", title: "K2", scenes: ["s3"] }] }],
  },
  scenes: {
    s1: { id: "s1", title: "Eins", summary: "", pov: "", status: "draft", text: "a", version: 2, updated_at: "" },
    s2: { id: "s2", title: "Zwei", summary: "", pov: "", status: "idea", text: "b", version: 5, updated_at: "" },
    s3: { id: "s3", title: "Drei", summary: "", pov: "", status: "done", text: "c", version: 1, updated_at: "" },
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
