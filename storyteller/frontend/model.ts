// Storyteller – Datenmodell und reine Hilfsfunktionen (ohne React, testbar).
// Spec: storyteller/docs/specs/stufe-1-grundoberflaeche.md (lokal).

export type BookKind = "novel" | "story" | "nonfiction" | "learning"
export type SceneStatus = "idea" | "draft" | "revised" | "done"
export type EntityKind = "character" | "place" | "item"

export interface Scene {
  id: string
  title: string
  summary: string
  pov: string
  status: SceneStatus
  text: string
}

export interface Chapter { id: string; title: string; scenes: Scene[] }
export interface Part { id: string; title: string; chapters: Chapter[] }

export interface Entity {
  id: string
  kind: EntityKind
  name: string
  aliases: string[]
  description: string
  fields: { key: string; value: string }[]
}

export interface Book {
  id: string
  title: string
  kind: BookKind
  language: string
  audience: string
  idea: string
  parts: Part[]
  entities: Entity[]
  notes: string
  updatedAt: string
}

export interface ScenePath { part: number; chapter: number; scene: number }

let seq = 0
/** Kurze, eindeutige ID im Browser (Entwurf; das Backend vergibt später echte IDs). */
export function newId(prefix: string): string {
  seq += 1
  return `${prefix}-${Date.now().toString(36)}-${seq.toString(36)}`
}

/** Wörter zählen wie der Editor: Folgen ohne Leerraum, Markdown-Zeichen ignoriert. */
export function countWords(markdown: string): number {
  const plain = markdown.replace(/[#>*_`~[\]()-]+/g, " ").trim()
  return plain ? plain.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length : 0
}

export function allScenes(book: Book): { path: ScenePath; scene: Scene; chapter: Chapter }[] {
  const out: { path: ScenePath; scene: Scene; chapter: Chapter }[] = []
  book.parts.forEach((p, pi) => p.chapters.forEach((c, ci) => c.scenes.forEach((s, si) =>
    out.push({ path: { part: pi, chapter: ci, scene: si }, scene: s, chapter: c }))))
  return out
}

export function findScene(book: Book, sceneId: string): { path: ScenePath; scene: Scene; chapter: Chapter } | null {
  return allScenes(book).find((x) => x.scene.id === sceneId) ?? null
}

export function bookWords(book: Book): number {
  return allScenes(book).reduce((n, x) => n + countWords(x.scene.text), 0)
}

export function chapterWords(chapter: Chapter): number {
  return chapter.scenes.reduce((n, s) => n + countWords(s.text), 0)
}

/** Unveränderlich: Szene per ID ersetzen. Unbekannte ID → Buch unverändert. */
export function updateScene(book: Book, sceneId: string, patch: Partial<Scene>): Book {
  return {
    ...book,
    parts: book.parts.map((p) => ({
      ...p,
      chapters: p.chapters.map((c) => ({
        ...c,
        scenes: c.scenes.map((s) => (s.id === sceneId ? { ...s, ...patch, id: s.id } : s)),
      })),
    })),
  }
}

/** Neue leere Szene hinter `afterSceneId` (oder am Ende des Kapitels). Liefert Buch + neue ID. */
export function addScene(book: Book, chapterId: string, afterSceneId?: string): { book: Book; id: string } {
  const id = newId("s")
  const fresh: Scene = { id, title: "Neue Szene", summary: "", pov: "", status: "idea", text: "" }
  const parts = book.parts.map((p) => ({
    ...p,
    chapters: p.chapters.map((c) => {
      if (c.id !== chapterId) return c
      const at = afterSceneId ? c.scenes.findIndex((s) => s.id === afterSceneId) + 1 : c.scenes.length
      const scenes = [...c.scenes]
      scenes.splice(at <= 0 ? c.scenes.length : at, 0, fresh)
      return { ...c, scenes }
    }),
  }))
  return { book: { ...book, parts }, id }
}

/** Neues Kapitel mit einer leeren Szene am Ende des Teils. */
export function addChapter(book: Book, partId: string, title = "Neues Kapitel"): { book: Book; sceneId: string } {
  const sceneId = newId("s")
  const chapter: Chapter = {
    id: newId("c"), title,
    scenes: [{ id: sceneId, title: "Szene 1", summary: "", pov: "", status: "idea", text: "" }],
  }
  return {
    book: { ...book, parts: book.parts.map((p) => (p.id === partId ? { ...p, chapters: [...p.chapters, chapter] } : p)) },
    sceneId,
  }
}

/**
 * Szene innerhalb des Buchs verschieben: vor `beforeSceneId` oder ans Ende von `toChapterId`.
 * Bleibt die Szene am selben Platz oder ist ein Ziel unbekannt, kommt das Buch unverändert zurück.
 */
export function moveScene(book: Book, sceneId: string, toChapterId: string, beforeSceneId?: string): Book {
  const found = findScene(book, sceneId)
  if (!found || beforeSceneId === sceneId) return book
  const target = book.parts.flatMap((p) => p.chapters).find((c) => c.id === toChapterId)
  if (!target) return book
  if (beforeSceneId && !target.scenes.some((s) => s.id === beforeSceneId)) return book
  const moving = found.scene
  const parts = book.parts.map((p) => ({
    ...p,
    chapters: p.chapters.map((c) => {
      let scenes = c.scenes.filter((s) => s.id !== sceneId)
      if (c.id === toChapterId) {
        const at = beforeSceneId ? scenes.findIndex((s) => s.id === beforeSceneId) : scenes.length
        scenes = [...scenes.slice(0, at), moving, ...scenes.slice(at)]
      }
      return { ...c, scenes }
    }),
  }))
  return { ...book, parts }
}

/** Szene eine Position nach oben (-1) oder unten (+1) im selben Kapitel (Tastatur: Alt+↑/↓). */
export function nudgeScene(book: Book, sceneId: string, delta: -1 | 1): Book {
  const found = findScene(book, sceneId)
  if (!found) return book
  const scenes = found.chapter.scenes
  const i = found.path.scene
  const j = i + delta
  if (j < 0 || j >= scenes.length) return book
  const before = delta === -1 ? scenes[j].id : scenes[j + 1]?.id
  return moveScene(book, sceneId, found.chapter.id, before)
}

/** Szene löschen. Die letzte Szene eines Kapitels bleibt (ein Kapitel ist nie leer). */
export function removeScene(book: Book, sceneId: string): Book {
  const found = findScene(book, sceneId)
  if (!found || found.chapter.scenes.length <= 1) return book
  return {
    ...book,
    parts: book.parts.map((p) => ({
      ...p, chapters: p.chapters.map((c) => ({ ...c, scenes: c.scenes.filter((s) => s.id !== sceneId) })),
    })),
  }
}

export function renameNode(book: Book, id: string, title: string): Book {
  const t = title.trim()
  if (!t) return book
  return {
    ...book,
    parts: book.parts.map((p) => ({
      ...(p.id === id ? { ...p, title: t } : p),
      chapters: p.chapters.map((c) => ({
        ...(c.id === id ? { ...c, title: t } : c),
        scenes: c.scenes.map((s) => (s.id === id ? { ...s, title: t } : s)),
      })),
    })),
  }
}

/** Steckbriefe, deren Name oder Spitzname im Text vorkommt (ganzes Wort, Groß/klein egal). */
export function entitiesInText(entities: Entity[], text: string): Entity[] {
  const lower = text.toLowerCase()
  return entities.filter((e) => [e.name, ...e.aliases].some((n) => {
    const needle = n.trim().toLowerCase()
    if (!needle) return false
    const re = new RegExp(`(^|[^\\p{L}\\p{N}])${needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}($|[^\\p{L}\\p{N}])`, "u")
    return re.test(lower)
  }))
}
