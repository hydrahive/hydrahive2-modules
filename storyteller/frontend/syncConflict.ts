// Versionskonflikte beim Speichern (Spec 1b §3): 409-Antwort einordnen und die Entscheidung des
// Nutzers anwenden. Reine Funktionen – BookSync ruft sie auf und hält den Zustand.
import type { ServerBook, ServerScene, ServerStructure } from "./api"
import { findScene, updateScene, type Book, type Scene } from "./model"
import { applyStructure, headFromServer, sceneFromServer, type Versions } from "./serverBook"

export type Conflict =
  | { kind: "scene"; sceneId: string; title: string; mine: Scene; theirs: ServerScene }
  | { kind: "structure"; theirs: ServerStructure }
  | { kind: "book"; theirs: ServerBook }

export function sceneMap(b: Book): Map<string, Scene> {
  return new Map(b.parts.flatMap((p) => p.chapters.flatMap((c) => c.scenes)).map((s) => [s.id, s]))
}

/** 409-Antwort einordnen: Struktur (hat parts), Buchkopf (hat kind+notes) oder Szene. */
export function toConflict(current: unknown, now: Book): Conflict {
  const c = (current ?? {}) as Record<string, unknown>
  if (Array.isArray(c.parts)) return { kind: "structure", theirs: c as unknown as ServerStructure }
  if (typeof c.kind === "string" && "notes" in c) return { kind: "book", theirs: c as unknown as ServerBook }
  const theirs = c as unknown as ServerScene
  const mine = findScene(now, theirs.id)?.scene ?? sceneFromServer(theirs)
  return { kind: "scene", sceneId: theirs.id, title: mine.title, mine, theirs }
}

/** Welcher Text vorher als Schnappschuss gesichert wird: bei „neu laden“ der eigene, bei
 *  „behalten“ der fremde. Nur bei Szenen-Konflikten. */
export function conflictSnapshot(c: Conflict, how: "reload" | "keep"): { sceneId: string; text: string } | null {
  if (c.kind !== "scene") return null
  return { sceneId: c.sceneId, text: how === "reload" ? c.mine.text : c.theirs.text }
}

/** Entscheidung anwenden. `saved` übernimmt immer den Server-Stand; `local` nur bei „neu laden“.
 *  Setzt die Version in `versions` auf die des Servers. */
export function applyResolution(c: Conflict, how: "reload" | "keep", saved: Book, local: Book, versions: Versions):
  { saved: Book; local: Book; reloadText: boolean } {
  const reload = how === "reload"
  if (c.kind === "scene") {
    versions.scenes[c.sceneId] = c.theirs.version
    const theirs = sceneFromServer(c.theirs)
    return {
      saved: updateScene(saved, c.sceneId, theirs),
      local: reload ? updateScene(local, c.sceneId, theirs) : local,
      reloadText: reload,
    }
  }
  if (c.kind === "structure") {
    versions.structure = c.theirs.version
    const take = (b: Book) => {
      const known = sceneMap(b)
      return { ...b, parts: applyStructure(c.theirs, (id) => known.get(id)), entities: c.theirs.entities }
    }
    return { saved: take(saved), local: reload ? take(local) : local, reloadText: false }
  }
  versions.book = c.theirs.version
  return { saved: headFromServer(saved, c.theirs), local: reload ? headFromServer(local, c.theirs) : local, reloadText: false }
}
