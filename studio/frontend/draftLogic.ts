/** Reine Hilfen für die Drehbuch-Entwürfe (B2), damit testbar. Grenzen wie auf dem Server (backend/draft_idea.py). */
import type { Draft, DraftBook } from "./draftApi"

export const MAX_IDEA = 2000
export const MAX_STYLE = 300

export function ideaValid(idea: string, style: string): boolean {
  return idea.trim().length > 0 && idea.length <= MAX_IDEA && style.length <= MAX_STYLE
}

export function draftCounts(d: Draft) {
  return { scenes: d.scenes.length, shots: d.scenes.reduce((n, s) => n + s.shots.length, 0), elements: d.elements.length }
}

export function toggleId(list: string[], id: string): string[] {
  return list.includes(id) ? list.filter((x) => x !== id) : [...list, id]
}

/** Zahl der Szenen in den gewählten Kapiteln. */
export function chosenScenes(book: DraftBook | null, chapters: string[]): number {
  return book ? book.chapters.filter((c) => chapters.includes(c.id)).reduce((n, c) => n + c.scenes, 0) : 0
}
