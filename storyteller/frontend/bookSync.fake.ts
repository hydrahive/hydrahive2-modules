// Gefälschter Storyteller-Server für bookSync.test.ts: hält Buch, Struktur, Szenen und Schnappschüsse
// im Speicher, prüft Versionen wie der echte Server (veraltet → 409 mit aktuellem Stand).
import { vi } from "vitest"
import { StoryApiError, type ServerBook, type ServerScene, type ServerStructure } from "./api"

export const scene = (id: string, text = ""): ServerScene => ({ id, title: id, summary: "", pov: "", status: "draft", origin: "human", text, version: 1, updated_at: "" })

export function fakeServer() {
  const db = {
    book: { id: "b", title: "T", kind: "novel", language: "de", audience: "", idea: "", notes: "", model: "",
      ghost: { model: "", length_words: 0, chunk_words: 0, style: "" }, version: 1, created_at: "", updated_at: "" } as ServerBook,
    structure: { version: 1, entities: [], parts: [{ id: "p", title: "Teil", chapters: [{ id: "c", title: "K", scenes: ["s1", "s2"] }] }] } as ServerStructure,
    scenes: { s1: scene("s1", "eins"), s2: scene("s2", "zwei") } as Record<string, ServerScene>,
    snapshots: [] as { sceneId: string; text: string }[],
  }
  const calls: string[] = []
  const conflict = (current: unknown) => new StoryApiError(409, "version_conflict", current)
  const api = {
    patchBook: vi.fn(async (_p: string, _b: string, v: number, patch: Partial<Omit<ServerBook, "ghost">> & { ghost?: Partial<ServerBook["ghost"]> }) => {
      calls.push("book")
      if (v !== db.book.version) throw conflict(db.book)
      db.book = { ...db.book, ...patch, ghost: { ...db.book.ghost, ...(patch.ghost ?? {}) }, version: v + 1 }
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
