// Beschriftungen je Buchart (Roman/Geschichte vs. Sach-/Lernbuch) und Buchsprache.
import type { BookKind, EntityKind } from "./model"

export interface DefaultNames { part: string; chapter: (n: number) => string; scene: (n: number) => string }

/** Namen für neue Teile/Kapitel/Szenen: in der Sprache des Buchs, Sachbuch „Abschnitt“ statt „Szene“. */
export function defaultNames(kind: BookKind, language: string): DefaultNames {
  const en = language.toLowerCase().startsWith("en")
  const fiction = isFiction(kind)
  return {
    part: en ? (fiction ? "Part 1" : "Contents") : (fiction ? "Teil 1" : "Inhalt"),
    chapter: (n) => (en ? `Chapter ${n}` : `Kapitel ${n}`),
    scene: (n) => (en ? (fiction ? `Scene ${n}` : `Section ${n}`) : (fiction ? `Szene ${n}` : `Abschnitt ${n}`)),
  }
}

export function isFiction(kind: BookKind): boolean {
  return kind === "novel" || kind === "story"
}

/** Beschriftung der Steckbrief-Gruppen: Sach-/Lernbuch nennt sie Personen/Begriffe/Quellen (Spec §6). */
export function groupLabelKey(kind: BookKind, entity: EntityKind): string {
  if (isFiction(kind)) return `group_${entity}`
  return { character: "group_person", place: "group_term", item: "group_source" }[entity]
}
