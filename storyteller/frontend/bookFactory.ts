// Neues Buch anlegen und Beschriftungen je Buchart (Roman/Geschichte vs. Sach-/Lernbuch).
import { newId, type Book, type BookKind, type EntityKind } from "./model"

/** Neues Buch mit Vorlage Teil → Kapitel → Szene (Sach-/Lernbuch: „Abschnitt“). */
export function blankBook(f: { title: string; kind: BookKind; language: string; audience: string; idea: string }): Book {
  const fiction = isFiction(f.kind)
  return {
    id: newId("b"), title: f.title.trim(), kind: f.kind, language: f.language, audience: f.audience.trim(),
    idea: f.idea.trim(), notes: "", updatedAt: new Date().toISOString(), entities: [],
    parts: [{
      id: newId("p"), title: fiction ? "Teil 1" : "Inhalt",
      chapters: [{
        id: newId("c"), title: "Kapitel 1",
        scenes: [{ id: newId("s"), title: fiction ? "Szene 1" : "Abschnitt 1", summary: "", pov: "", status: "idea", text: "" }],
      }],
    }],
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
