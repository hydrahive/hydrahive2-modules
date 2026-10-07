// Storyteller – Datenmodell und reine Hilfsfunktionen (ohne React, testbar).
// Spec: storyteller/docs/specs/stufe-1-grundoberflaeche.md + stufe-1b-ablage-ki.md (lokal).

export type BookKind = "novel" | "story" | "nonfiction" | "learning"
export type SceneStatus = "idea" | "draft" | "revised" | "done"
export type EntityKind = "character" | "place" | "item"
/** Herkunft des Szenentexts: eigener Text, KI-Entwurf (Ghostwriter), vom Menschen bearbeiteter KI-Entwurf. */
export type SceneOrigin = "human" | "ai_draft" | "ai_edited"

export interface Scene {
  id: string
  title: string
  summary: string
  pov: string
  status: SceneStatus
  origin: SceneOrigin
  text: string
}

/** Ghostwriter-Einstellungen je Buch (leer/0 = nicht gesetzt; kein festes Modell im Code).
 *  limit_tokens: Kostengrenze je Lauf in Ausgabe-Tokens, 0 = keine. */
export interface GhostSettings { model: string; length_words: number; chunk_words: number; style: string; limit_tokens: number }
export const GHOST_EMPTY: GhostSettings = { model: "", length_words: 0, chunk_words: 0, style: "", limit_tokens: 0 }

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
  /** KI-Modell des Buchs; leer = HydraHive-Standardmodell für Chat. */
  model: string
  ghost: GhostSettings
  updatedAt: string
}

export interface ScenePath { part: number; chapter: number; scene: number }

/** ID wie auf dem Server: 32 Hex-Zeichen (z. B. für neue Steckbriefe). */
export function newId(): string {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("")
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

/** Herkunft nach einer Textänderung durch den Menschen: KI-Entwurf wird „bearbeitet“. */
export function originAfterEdit(origin: SceneOrigin): SceneOrigin {
  return origin === "ai_draft" ? "ai_edited" : origin
}

/** Anteil der Wörter in Szenen mit KI-Herkunft (0–100, gerundet). */
export function aiShare(book: Book): number {
  let ai = 0
  let all = 0
  for (const { scene } of allScenes(book)) {
    const w = countWords(scene.text)
    all += w
    if (scene.origin !== "human") ai += w
  }
  return all ? Math.round((ai / all) * 100) : 0
}
