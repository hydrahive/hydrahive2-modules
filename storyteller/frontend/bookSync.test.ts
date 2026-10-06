// BookSync gegen einen nachgebauten Server (gleiche Regeln wie das Backend: Version passt → +1,
// sonst 409 mit aktuellem Stand). Prüft: nur Geändertes wird gesendet, Konflikt stoppt das
// Speichern, beide Auflösungen verlieren nichts.
import { beforeEach, describe, expect, it, vi } from "vitest"
import { BookSync, type SyncView } from "./bookSync"
import { fakeServer, scene } from "./bookSync.fake"
import { findScene, updateScene, type Book } from "./model"
import { fromServer } from "./serverBook"

vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "", logout: () => {} }) } }))

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
    expect(view?.textRev).toBe(1)  // Editor muss den fremden Text neu laden
  })

  it("„meine behalten“ lädt den Editor nicht neu; Text von außen ersetzen schon", async () => {
    srv.db.scenes.s1 = { ...srv.db.scenes.s1, text: "vom Agenten", version: 2 }
    sync.edit(updateScene(sync.book, "s1", { text: "meins" }))
    await sync.flush()
    await sync.resolve("keep")
    expect(view?.textRev).toBe(0)
    sync.replaceText("s1", "alter Stand")
    expect(view?.textRev).toBe(1)
    expect(text(sync.book, "s1")).toBe("alter Stand")
    await sync.flush()
    expect(srv.db.scenes.s1.text).toBe("alter Stand")
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

describe("BookSync – Ghostwriter-Einstellungen", () => {
  it("speichert nur die geänderte Einstellung, andere bleiben", async () => {
    sync.edit({ ...sync.book, ghost: { ...sync.book.ghost, length_words: 1500 } })
    await sync.flush()
    expect(srv.calls).toEqual(["book"])
    expect(srv.db.book.ghost).toEqual({ model: "", length_words: 1500, chunk_words: 0, style: "" })
    sync.edit({ ...sync.book, ghost: { ...sync.book.ghost, style: "knapp" } })
    await sync.flush()
    expect(srv.db.book.ghost).toEqual({ model: "", length_words: 1500, chunk_words: 0, style: "knapp" })
    expect(srv.api.patchBook.mock.calls[1][3]).toEqual({ ghost: { style: "knapp" } })
  })
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
