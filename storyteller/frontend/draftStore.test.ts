import { beforeEach, describe, expect, it, vi } from "vitest"
import type { Book } from "./model"
import { draftStore } from "./draftStore"
import { lastPlace } from "./lastPlace"

const mem = new Map<string, string>()
vi.stubGlobal("localStorage", {
  getItem: (k: string) => mem.get(k) ?? null,
  setItem: (k: string, v: string) => { mem.set(k, v) },
  removeItem: (k: string) => { mem.delete(k) },
})

const book = (id: string, title = id): Book => ({
  id, title, kind: "novel", language: "de", audience: "", idea: "", notes: "", model: "", updatedAt: "",
  parts: [], entities: [],
})
const seed = (projectId: string, books: object[]) =>
  mem.set(`storyteller.draft.v1.${projectId}`, JSON.stringify({ books, last: { bookId: "a", sceneId: "s" } }))

describe("draftStore (Bücher aus dem Entwurf 0.1.0, nur zur Übernahme)", () => {
  beforeEach(() => mem.clear())

  it("liest je Projekt getrennt und füllt fehlende Felder (alte Bücher haben kein model)", () => {
    const { model: _m, ...old } = book("a")
    seed("p1", [old])
    expect(draftStore.list("p1")).toEqual([book("a")])
    expect(draftStore.list("p2")).toEqual([])
  })
  it("vergisst nur die übernommenen Bücher, den Rest nicht; leer → Eintrag weg", () => {
    seed("p", [book("a"), book("b")])
    expect(draftStore.forget("p", ["a"])).toBe(true)
    expect(draftStore.list("p").map((b) => b.id)).toEqual(["b"])
    expect(draftStore.forget("p", ["b"])).toBe(true)
    expect(mem.has("storyteller.draft.v1.p")).toBe(false)
  })
  it("kaputte Daten im Speicher führen nicht zum Absturz", () => {
    mem.set("storyteller.draft.v1.p", "{kaputt")
    expect(draftStore.list("p")).toEqual([])
  })
  it("meldet fehlgeschlagenes Schreiben statt still zu verlieren", () => {
    seed("p", [book("a"), book("b")])
    const orig = localStorage.setItem
    localStorage.setItem = () => { throw new Error("QuotaExceededError") }
    expect(draftStore.forget("p", ["a"])).toBe(false)
    localStorage.setItem = orig
  })
})

describe("lastPlace (zuletzt geöffnete Szene)", () => {
  beforeEach(() => mem.clear())
  it("merkt sich je Projekt eine Stelle und vergisst sie mit dem Buch", () => {
    lastPlace.set("p", "b1", "s1")
    expect(lastPlace.get("p")).toEqual({ bookId: "b1", sceneId: "s1" })
    expect(lastPlace.get("q")).toBeUndefined()
    lastPlace.clear("p", "anderes")
    expect(lastPlace.get("p")).toBeDefined()
    lastPlace.clear("p", "b1")
    expect(lastPlace.get("p")).toBeUndefined()
  })
  it("Unsinn im Speicher → nichts", () => {
    mem.set("storyteller.last.v2.p", "[1,2]")
    expect(lastPlace.get("p")).toBeUndefined()
  })
})
