// BookSync für den Ghostwriter: Text mit Herkunft setzen, Server-Szene/-Gliederung übernehmen,
// Szenen-Version abfragen. Gleicher nachgebauter Server wie bookSync.test.ts.
import { beforeEach, describe, expect, it, vi } from "vitest"
import { BookSync, type SyncView } from "./bookSync"
import { fakeServer, scene } from "./bookSync.fake"
import { findScene, updateScene } from "./model"
import { fromServer } from "./serverBook"

vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "", logout: () => {} }) } }))

let srv: ReturnType<typeof fakeServer>
let view: SyncView | null
let sync: BookSync

beforeEach(() => {
  srv = fakeServer()
  view = null
  const { book, versions } = fromServer({ book: srv.db.book, structure: srv.db.structure, scenes: srv.db.scenes })
  sync = new BookSync("p", book, versions, (v) => { view = v }, srv.api, 1000)
})

describe("BookSync – Text mit Herkunft und Server-Szene übernehmen", () => {
  it("replaceText mit Herkunft: Editor lädt neu, origin wird gespeichert", async () => {
    sync.replaceText("s1", "KI-Szene", "ai_draft")
    expect(view?.textRev).toBe(1)
    await sync.flush()
    expect(srv.db.scenes.s1).toMatchObject({ text: "KI-Szene", origin: "ai_draft", version: 2 })
  })
  it("adoptScene übernimmt Server-Stand (Version + Felder) ohne erneutes Speichern", async () => {
    const fromServerSide = { ...srv.db.scenes.s2, summary: "neu vom Server", version: 7 }
    sync.adoptScene(fromServerSide)
    expect(findScene(sync.book, "s2")?.scene.summary).toBe("neu vom Server")
    await sync.flush()
    expect(srv.calls).toEqual([])                       // nichts zu speichern
    sync.edit(updateScene(sync.book, "s2", { text: "weiter" }))
    await sync.flush()
    expect(srv.api.putScene.mock.calls[0][3]).toBe(7)    // baut auf der übernommenen Version auf
  })
  it("adoptScene behält ungespeicherte eigene Änderungen an anderen Feldern", () => {
    sync.edit(updateScene(sync.book, "s2", { text: "noch nicht gespeichert" }))
    sync.adoptScene({ ...srv.db.scenes.s2, summary: "Server", version: 2 })
    expect(findScene(sync.book, "s2")?.scene).toMatchObject({ summary: "Server", text: "noch nicht gespeichert" })
  })
})

describe("BookSync – Gliederung übernommen, Szenen-Version (G2)", () => {
  it("adoptStructure mit mehreren neuen Szenen übernimmt alle (Versionen inklusive)", async () => {
    const a = scene("s3"), b = { ...scene("s4"), version: 4 }
    srv.db.scenes.s3 = a
    srv.db.scenes.s4 = b
    const st = { ...srv.db.structure, version: 2,
      parts: [{ id: "p", title: "Teil", chapters: [...srv.db.structure.parts[0].chapters, { id: "c2", title: "Neu", scenes: ["s3", "s4"] }] }] }
    srv.db.structure = st
    sync.adoptStructure(st, [a, b])
    expect(findScene(sync.book, "s4")?.scene.id).toBe("s4")
    sync.edit(updateScene(sync.book, "s4", { text: "los" }))
    await sync.flush()
    expect(srv.api.putScene.mock.calls[0][3]).toBe(4)
  })
  it("sceneVersion liefert die Version, auf der gerade aufgebaut wird", async () => {
    expect(sync.sceneVersion("s1")).toBe(1)
    sync.edit(updateScene(sync.book, "s1", { text: "neu" }))
    await sync.flush()
    expect(sync.sceneVersion("s1")).toBe(2)
    expect(sync.sceneVersion("gibt-es-nicht")).toBeUndefined()
  })
})

describe("BookSync – Editor neu laden und Struktur-Version (G2)", () => {
  it("reloadText erhöht textRev ohne etwas zu speichern", async () => {
    sync.reloadText()
    expect(view?.textRev).toBe(1)
    await sync.flush()
    expect(srv.calls).toEqual([])
  })
  it("structureVersion folgt adoptStructure", () => {
    expect(sync.structureVersion()).toBe(1)
    sync.adoptStructure({ ...srv.db.structure, version: 5 })
    expect(sync.structureVersion()).toBe(5)
  })
})
