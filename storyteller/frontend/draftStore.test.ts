import { beforeEach, describe, expect, it, vi } from "vitest"
import type { Book } from "./model"
import { draftStore } from "./draftStore"

const mem = new Map<string, string>()
vi.stubGlobal("localStorage", {
  getItem: (k: string) => mem.get(k) ?? null,
  setItem: (k: string, v: string) => { mem.set(k, v) },
  removeItem: (k: string) => { mem.delete(k) },
})

const book = (id: string, title = id): Book => ({
  id, title, kind: "novel", language: "de", audience: "", idea: "", notes: "", updatedAt: "",
  parts: [], entities: [],
})

describe("draftStore (Entwurf, Browser-Ablage)", () => {
  beforeEach(() => mem.clear())

  it("trennt Projekte strikt", () => {
    draftStore.save("p1", book("a"))
    expect(draftStore.list("p1").map((b) => b.id)).toEqual(["a"])
    expect(draftStore.list("p2")).toEqual([])
    expect(draftStore.get("p2", "a")).toBeNull()
  })
  it("speichert, aktualisiert und löscht; „zuletzt“ verschwindet mit dem Buch", () => {
    draftStore.save("p", book("a", "Alt"))
    draftStore.save("p", book("a", "Neu"))
    expect(draftStore.list("p")).toHaveLength(1)
    expect(draftStore.get("p", "a")?.title).toBe("Neu")
    draftStore.setLast("p", "a", "s1")
    expect(draftStore.last("p")).toEqual({ bookId: "a", sceneId: "s1" })
    draftStore.remove("p", "a")
    expect(draftStore.list("p")).toEqual([])
    expect(draftStore.last("p")).toBeUndefined()
  })
  it("kaputte Daten im Speicher führen nicht zum Absturz", () => {
    mem.set("storyteller.draft.v1.p", "{kaputt")
    expect(draftStore.list("p")).toEqual([])
  })
  it("meldet fehlgeschlagenes Speichern statt still zu verlieren", () => {
    const orig = localStorage.setItem
    localStorage.setItem = () => { throw new Error("QuotaExceededError") }
    expect(draftStore.save("p", book("a"))).toBe(false)
    localStorage.setItem = orig
    expect(draftStore.save("p", book("a"))).toBe(true)
  })
})
