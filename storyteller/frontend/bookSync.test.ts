// BookSync gegen einen nachgebauten Server (gleiche Regeln wie das Backend: Version passt → +1,
// sonst 409 mit aktuellem Stand). Prüft: nur Geändertes wird gesendet, Konflikt stoppt das
// Speichern, beide Auflösungen verlieren nichts.
import { beforeEach, describe, expect, it, vi } from "vitest"
import { StoryApiError, type ServerBook, type ServerScene, type ServerStructure } from "./api"
import { BookSync, type SyncView } from "./bookSync"
import { findScene, updateScene, type Book } from "./model"
import { fromServer } from "./serverBook"

vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "", logout: () => {} }) } }))

const scene = (id: string, text = ""): ServerScene => ({ id, title: id, summary: "", pov: "", status: "draft", text, version: 1, updated_at: "" })

function fakeServer() {
  const db = {
    book: { id: "b", title: "T", kind: "novel", language: "de", audience: "", idea: "", notes: "", model: "", version: 1, created_at: "", updated_at: "" } as ServerBook,
    structure: { version: 1, entities: [], parts: [{ id: "p", title: "Teil", chapters: [{ id: "c", title: "K", scenes: ["s1", "s2"] }] }] } as ServerStructure,
    scenes: { s1: scene("s1", "eins"), s2: scene("s2", "zwei") } as Record<string, ServerScene>,
    snapshots: [] as { sceneId: string; text: string }[],
  }
  const calls: string[] = []
  const conflict = (current: unknown) => new StoryApiError(409, "version_conflict", current)
  const api = {
    patchBook: vi.fn(async (_p: string, _b: string, v: number, patch: Partial<ServerBook>) => {
      calls.push("book")
      if (v !== db.book.version) throw conflict(db.book)
      db.book = { ...db.book, ...patch, version: v + 1 }
      return db.book
    }),
    putScene: vi.fn(async (_p: string, _b: string, id: string, v: number, patch: Partial<ServerScene>) => {
      calls.push(`scene:${id}`)
      if (v !== db.scenes[id].version) throw conflict(db.scenes[id])
      db.scenes[id] = { ...db.scenes[id], ...patch, version: v + 1 }
      return db.scenes[id]
    }),
    putStructure: vi.fn(async (_p: string, _b: string, v: number, st: Omit<ServerStructure, "version">) => {
      calls.push("structure")
      if (v !== db.structure.version) throw conflict(db.structure)
      db.structure = { ...st, version: v + 1 }
      return db.structure
    }),
    addSnapshot: vi.fn(async (_p: string, _b: string, sceneId: string, text?: string) => {
      db.snapshots.push({ sceneId, text: text ?? "" })
      return { id: "x", at: "", words: 0 }
    }),
  }
  return { db, api, calls }
}

let srv: ReturnType<typeof fakeServer>
let view: SyncView | null
let sync: BookSync
const open = () => fromServer({ book: srv.db.book, structure: srv.db.structure, scenes: srv.db.scenes })

beforeEach(() => {
  srv = fakeServer()
  view = null
  const { book, versions } = open()
  sync = new BookSync("p", book, versions, (v) => { view = v }, srv.api, 1000)
  vi.useRealTimers()
})

const text = (b: Book, id: string) => findScene(b, id)?.scene.text

describe("BookSync", () => {
  it("speichert nur die geänderte Szene, nicht Struktur oder Kopf", async () => {
    sync.edit(updateScene(sync.book, "s1", { text: "eins neu" }))
    expect(view?.saveState).toBe("saving")
    await sync.flush()
    expect(srv.calls).toEqual(["scene:s1"])
    expect(srv.db.scenes.s1).toMatchObject({ text: "eins neu", version: 2 })
    expect(view?.saveState).toBe("saved")
    await sync.flush()
    expect(srv.calls).toHaveLength(1)  // nichts mehr zu tun
  })

  it("speichert erst 1 s nach der letzten Änderung (mehrere Tastendrücke → 1 Aufruf)", async () => {
    vi.useFakeTimers()
    sync.edit(updateScene(sync.book, "s1", { text: "a" }))
    vi.advanceTimersByTime(500)
    sync.edit(updateScene(sync.book, "s1", { text: "ab" }))
    vi.advanceTimersByTime(999)
    expect(srv.calls).toEqual([])
    await vi.advanceTimersByTimeAsync(1)
    expect(srv.calls).toEqual(["scene:s1"])
    expect(srv.db.scenes.s1.text).toBe("ab")
  })

  it("Verschieben/Umbenennen/Steckbriefe gehen über die Struktur, Titel über den Kopf", async () => {
    const b = sync.book
    const ch = b.parts[0].chapters[0]
    sync.edit({ ...b, title: "Neu", parts: [{ ...b.parts[0], chapters: [{ ...ch, scenes: [...ch.scenes].reverse() }] }] })
    await sync.flush()
    expect(srv.calls.sort()).toEqual(["book", "structure"])
    expect(srv.db.structure.parts[0].chapters[0].scenes).toEqual(["s2", "s1"])
    expect(srv.db.book.title).toBe("Neu")
  })

  it("leerer Titel / Steckbrief ohne Namen → Fehler sichtbar, kein Aufruf", async () => {
    sync.edit({ ...sync.book, title: "  " })
    await sync.flush()
    expect(view).toMatchObject({ saveState: "failed", saveError: "title_required" })
    expect(srv.calls).toEqual([])
  })

  it("fremde Änderung → Konflikt, danach wird nichts mehr gespeichert", async () => {
    srv.db.scenes.s1 = { ...srv.db.scenes.s1, text: "vom Agenten", version: 2 }
    sync.edit(updateScene(sync.book, "s1", { text: "meins" }))
    await sync.flush()
    expect(view?.saveState).toBe("conflict")
    expect(view?.conflict).toMatchObject({ kind: "scene", sceneId: "s1" })
    sync.edit(updateScene(sync.book, "s2", { text: "weiter getippt" }))
    await sync.flush()
    expect(srv.calls).toEqual(["scene:s1"])  // gesperrt bis zur Entscheidung
    expect(text(sync.book, "s2")).toBe("weiter getippt")  // Eingabe bleibt sichtbar
  })

  it("Konflikt „neu laden“: Server-Text übernehmen, eigene Fassung als Schnappschuss", async () => {
    srv.db.scenes.s1 = { ...srv.db.scenes.s1, text: "vom Agenten", version: 2 }
    sync.edit(updateScene(sync.book, "s1", { text: "meins" }))
    await sync.flush()
    await sync.resolve("reload")
    expect(srv.db.snapshots).toEqual([{ sceneId: "s1", text: "meins" }])
    expect(text(sync.book, "s1")).toBe("vom Agenten")
    expect(srv.db.scenes.s1).toMatchObject({ text: "vom Agenten", version: 2 })
    expect(view?.conflict).toBeNull()
  })

  it("Konflikt „meine behalten“: fremde Fassung als Schnappschuss, dann eigene speichern", async () => {
    srv.db.scenes.s1 = { ...srv.db.scenes.s1, text: "vom Agenten", version: 2 }
    sync.edit(updateScene(sync.book, "s1", { text: "meins" }))
    await sync.flush()
    await sync.resolve("keep")
    expect(srv.db.snapshots).toEqual([{ sceneId: "s1", text: "vom Agenten" }])
    expect(srv.db.scenes.s1).toMatchObject({ text: "meins", version: 3 })
    expect(view?.saveState).toBe("saved")
  })

  it("Struktur-Konflikt „neu laden“ übernimmt die fremde Reihenfolge", async () => {
    srv.db.structure = { ...srv.db.structure, version: 2, parts: [{ id: "p", title: "Teil", chapters: [{ id: "c", title: "Anders", scenes: ["s2", "s1"] }] }] }
    sync.edit({ ...sync.book, entities: [{ id: "e".repeat(32), kind: "place", name: "Ort", aliases: [], description: "", fields: [] }] })
    await sync.flush()
    expect(view?.conflict?.kind).toBe("structure")
    await sync.resolve("reload")
    expect(sync.book.parts[0].chapters[0].title).toBe("Anders")
    expect(sync.book.parts[0].chapters[0].scenes.map((s) => s.id)).toEqual(["s2", "s1"])
  })

  it("Netzfehler → „fehlgeschlagen“, Text bleibt; nochmal speichern klappt", async () => {
    srv.api.putScene.mockRejectedValueOnce(new Error("offline"))
    sync.edit(updateScene(sync.book, "s1", { text: "wichtig" }))
    await sync.flush()
    expect(view?.saveState).toBe("failed")
    expect(text(sync.book, "s1")).toBe("wichtig")
    await sync.flush()
    expect(srv.db.scenes.s1.text).toBe("wichtig")
    expect(view?.saveState).toBe("saved")
  })

  it("vom Server angelegte Szene wird übernommen, ohne ungespeicherten Text zu verlieren", async () => {
    sync.edit(updateScene(sync.book, "s1", { text: "noch nicht gespeichert" }))
    const added = scene("s3")
    const st = { ...srv.db.structure, version: 2, parts: [{ id: "p", title: "Teil", chapters: [{ id: "c", title: "K", scenes: ["s1", "s2", "s3"] }] }] }
    srv.db.structure = st
    srv.db.scenes.s3 = added
    sync.adoptStructure(st, added)
    expect(sync.book.parts[0].chapters[0].scenes.map((s) => s.id)).toEqual(["s1", "s2", "s3"])
    expect(text(sync.book, "s1")).toBe("noch nicht gespeichert")
    await sync.flush()
    expect(srv.calls).toEqual(["scene:s1"])  // keine Struktur-Speicherung nötig (Version 2 übernommen)
  })
})
