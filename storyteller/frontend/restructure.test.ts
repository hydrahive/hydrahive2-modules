// C2 – Umbau-Vorschlag des Autors und Schalter „direkt ändern“ (Spec autor-gliederung-c2.md §2b) – ohne React.
import { afterEach, describe, expect, it, vi } from "vitest"
import { agentStructure, chapterDiff, needsStructureReload, restructureApi, withAgentStructure } from "./restructure"
import { GHOST_EMPTY, type Book } from "./model"

const respond = (status: number, body: unknown) =>
  vi.fn(async (_url: string, _init?: RequestInit) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }))
afterEach(() => vi.unstubAllGlobals())

describe("Schalter je Buch", () => {
  it("Standard ist Vorschlag; nur „direct“ ist direkt", () => {
    expect(agentStructure(GHOST_EMPTY)).toBe("propose")
    expect(agentStructure({ ...GHOST_EMPTY, agent_structure: "direct" })).toBe("direct")
    expect(agentStructure({ ...GHOST_EMPTY, agent_structure: "quatsch" as never })).toBe("propose")
  })
  it("setzt den Schalter im Buch, ohne die übrigen Einstellungen anzufassen", () => {
    const b = { ghost: { ...GHOST_EMPTY, limit_tokens: 5000 } } as Book
    expect(withAgentStructure(b, true).ghost).toEqual({ ...GHOST_EMPTY, limit_tokens: 5000, agent_structure: "direct" })
    expect(withAgentStructure(b, false).ghost.agent_structure).toBe("propose")
  })
})

describe("Vorher/Nachher", () => {
  it("markiert neue, weggefallene und gebliebene Kapitel (nach Titel, Reihenfolge des Nachher)", () => {
    expect(chapterDiff(["Anfang", "Mitte", "Ende"], ["Der Anfang", "Mitte", "Ende", "Epilog"])).toEqual({
      after: [{ title: "Der Anfang", kind: "new" }, { title: "Mitte", kind: "same" }, { title: "Ende", kind: "same" },
              { title: "Epilog", kind: "new" }],
      gone: ["Anfang"],
    })
    expect(chapterDiff(["A", "B"], ["A", "B"])).toEqual({ after: [{ title: "A", kind: "same" }, { title: "B", kind: "same" }], gone: [] })
  })
})

describe("Direkte Änderung des Autors bemerken", () => {
  it("neu holen nur, wenn der Server weiter ist und lokal nichts ungespeichert ist", () => {
    expect(needsStructureReload(5, 6, false)).toBe(true)
    expect(needsStructureReload(5, 5, false)).toBe(false)
    expect(needsStructureReload(5, 6, true)).toBe(false)       // Ungespeichertes → Konflikt-Dialog beim Speichern
    expect(needsStructureReload(6, 5, false)).toBe(false)
  })
})

describe("restructureApi", () => {
  it("offener Vorschlag: Inhalt bzw. null (Server liefert null, wenn keiner da ist)", async () => {
    vi.stubGlobal("fetch", respond(200, null))
    expect(await restructureApi.get("p", "b")).toBeNull()
    const prop = { steps: [], lines: ["x"], before: ["A"], after: ["B"], base_structure_version: 3, source: "agent",
                   author: "Autor", note: "", session_id: "", at: "t" }
    const f = respond(200, prop)
    vi.stubGlobal("fetch", f)
    expect(await restructureApi.get("p", "b")).toEqual(prop)
    expect(String(f.mock.calls[0][0])).toMatch(/\/projects\/p\/books\/b\/proposals\/restructure$/)
  })
  it("übernehmen (POST …/accept) und verwerfen (DELETE)", async () => {
    const f = respond(200, { structure: { version: 4, parts: [], entities: [] }, scenes: [], ids: {}, lines: [] })
    vi.stubGlobal("fetch", f)
    await restructureApi.accept("p", "b")
    expect(String(f.mock.calls[0][0])).toMatch(/\/proposals\/restructure\/accept$/)
    expect(f.mock.calls[0][1]?.method).toBe("POST")
    const g = respond(200, { ok: true })
    vi.stubGlobal("fetch", g)
    await restructureApi.discard("p", "b")
    expect(g.mock.calls[0][1]?.method).toBe("DELETE")
  })
  it("Fehler mit Code (z. B. Plan passt nicht mehr) wird geworfen", async () => {
    vi.stubGlobal("fetch", respond(404, { detail: { code: "scene_not_found" } }))
    await expect(restructureApi.accept("p", "b")).rejects.toMatchObject({ code: "scene_not_found" })
  })
})
