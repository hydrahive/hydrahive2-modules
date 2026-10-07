// Umrechnung zwischen Server-Ablage (Kopf, Struktur mit Szenen-IDs, Szenen einzeln) und dem
// verschachtelten Buchmodell der Oberfläche. Rein, ohne React → testbar.
import type { ServerBook, ServerFull, ServerScene, ServerStructure } from "./api"
import { infoMarks } from "./infoProposal"
import { markOf, type ProposalMark } from "./proposalMark"
import { allScenes, GHOST_EMPTY, type Book, type GhostSettings, type Scene } from "./model"

export interface Versions { book: number; structure: number; scenes: Record<string, number> }

const HEAD_FIELDS = ["title", "audience", "idea", "notes", "model"] as const
const SCENE_FIELDS = ["title", "summary", "pov", "status", "origin", "text"] as const
export type HeadPatch = Partial<Pick<Book, (typeof HEAD_FIELDS)[number]>> & { ghost?: Partial<GhostSettings> }
export type ScenePatch = Partial<Pick<Scene, (typeof SCENE_FIELDS)[number]>>

export function sceneFromServer(s: ServerScene): Scene {
  return { id: s.id, title: s.title, summary: s.summary, pov: s.pov, status: s.status, origin: s.origin ?? "human", text: s.text }
}

export function fromServer(full: ServerFull): { book: Book; versions: Versions } {
  const { book: h, structure, scenes } = full
  const book: Book = {
    id: h.id, title: h.title, kind: h.kind, language: h.language, audience: h.audience, idea: h.idea,
    notes: h.notes, model: h.model ?? "", ghost: { ...GHOST_EMPTY, ...(h.ghost ?? {}) }, updatedAt: h.updated_at,
    entities: structure.entities.map((e) => ({ ...e, aliases: [...e.aliases], fields: e.fields.map((f) => ({ ...f })) })),
    parts: applyStructure(structure, (id) => (scenes[id] ? sceneFromServer(scenes[id]) : undefined)),
  }
  const versions: Versions = {
    book: h.version, structure: structure.version,
    scenes: Object.fromEntries(Object.values(scenes).map((s) => [s.id, s.version])),
  }
  return { book, versions }
}

/** Teile/Kapitel aus der Server-Struktur; Szenen kommen aus `sceneOf` (unbekannte IDs fallen weg). */
export function applyStructure(st: ServerStructure, sceneOf: (id: string) => Scene | undefined): Book["parts"] {
  return st.parts.map((p) => ({
    id: p.id, title: p.title,
    chapters: p.chapters.map((c) => ({
      id: c.id, title: c.title,
      scenes: c.scenes.map(sceneOf).filter((s): s is Scene => !!s),
    })),
  }))
}

export function toStructure(book: Book): Omit<ServerStructure, "version"> {
  return {
    parts: book.parts.map((p) => ({
      id: p.id, title: p.title,
      chapters: p.chapters.map((c) => ({ id: c.id, title: c.title, scenes: c.scenes.map((s) => s.id) })),
    })),
    entities: book.entities.map((e) => ({ ...e })),
  }
}

/** Gibt es irgendetwas zu speichern (Kopf, Szenen oder Struktur)? */
export function hasChanges(now: Book, saved: Book): boolean {
  return Object.keys(headPatch(now, saved)).length > 0 || scenePatches(now, saved).length > 0 || structureChanged(now, saved)
}

export function structureChanged(a: Book, b: Book): boolean {
  return JSON.stringify(toStructure(a)) !== JSON.stringify(toStructure(b))
}

export function headPatch(now: Book, saved: Book): HeadPatch {
  const out: HeadPatch = {}
  for (const k of HEAD_FIELDS) if (now[k] !== saved[k]) out[k] = now[k]
  const g: Partial<GhostSettings> = {}
  for (const k of Object.keys(GHOST_EMPTY) as (keyof GhostSettings)[]) {
    if (now.ghost[k] !== saved.ghost[k]) (g as Record<string, unknown>)[k] = now.ghost[k]
  }
  if (Object.keys(g).length) out.ghost = g
  return out
}

/** Geänderte Felder je Szene (nur Szenen, die es in beiden Ständen gibt). */
export function scenePatches(now: Book, saved: Book): { id: string; patch: ScenePatch }[] {
  const before = new Map(allScenes(saved).map((x) => [x.scene.id, x.scene]))
  const out: { id: string; patch: ScenePatch }[] = []
  for (const { scene } of allScenes(now)) {
    const old = before.get(scene.id)
    if (!old) continue
    const patch: ScenePatch = {}
    for (const k of SCENE_FIELDS) if (scene[k] !== old[k]) (patch as Record<string, unknown>)[k] = scene[k]
    if (Object.keys(patch).length) out.push({ id: scene.id, patch })
  }
  return out
}

/** Warum die Struktur (noch) nicht gespeichert werden kann – leer = alles gut. */
export function structureProblem(book: Book): string {
  if (book.entities.some((e) => !e.name.trim())) return "entity_name_required"
  return ""
}

export function headFromServer(book: Book, h: ServerBook): Book {
  return { ...book, title: h.title, audience: h.audience, idea: h.idea, notes: h.notes, model: h.model ?? "",
    ghost: { ...GHOST_EMPTY, ...(h.ghost ?? {}) }, updatedAt: h.updated_at }
}

/** Ganzes Buch für POST …/books/import (Beispielbuch, Übernahme aus dem Entwurf). */
export function toImport(book: Book) {
  return {
    title: book.title, kind: book.kind, language: book.language, audience: book.audience, idea: book.idea,
    notes: book.notes, model: book.model ?? "",
    parts: book.parts.map((p) => ({
      title: p.title,
      chapters: p.chapters.map((c) => ({
        title: c.title,
        scenes: c.scenes.map((s) => ({ title: s.title, summary: s.summary, pov: s.pov, status: s.status, origin: s.origin, text: s.text })),
      })),
    })),
    entities: book.entities.map(({ kind, name, aliases, description, fields }) => ({ kind, name, aliases, description, fields })),
  }
}

export type { ProposalMark } from "./proposalMark"

/** Alles, was beim Öffnen gebraucht wird: Buch, Versionen, Schreibrecht, offene Vorschläge.
 *  Ältere Server (vor 0.4.0) liefern die neuen Felder nicht: dann Schreiben erlaubt, keine Vorschläge. */
export function openedFromServer(full: ServerFull) {
  const { book, versions } = fromServer(full)
  const proposals: Record<string, ProposalMark> = {}
  for (const p of full.proposals ?? []) {
    proposals[p.scene_id] = markOf(p)
  }
  return { book, versions, canWrite: full.can_write ?? true, proposals, infoProposals: infoMarks(full.info_proposals),
    entityProposals: full.entity_proposals ?? [], outlineProposal: full.outline_proposal ?? null,
    openNotes: full.open_notes ?? {} }
}
