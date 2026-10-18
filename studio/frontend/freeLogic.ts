/** Reine Hilfen für „Freies Bild“ (B3), damit testbar. Grenzen wie auf dem Server (backend/free_images.py). */
import type { LibraryItem } from "./api"
import type { Plan } from "./planApi"

export const MAX_FREE_PROMPT = 2000
export const MAX_FREE_COUNT = 4
export const MAX_FREE_REFS = 3

export interface FreeFormState { prompt: string; model: string; aspect: string; count: number; refs: string[] }

export function freeValid(f: FreeFormState): boolean {
  return f.prompt.trim().length > 0 && f.prompt.length <= MAX_FREE_PROMPT && f.count >= 1 && f.count <= MAX_FREE_COUNT
}

export function toggleRef(refs: string[], rel: string): string[] {
  if (refs.includes(rel)) return refs.filter((r) => r !== rel)
  return refs.length >= MAX_FREE_REFS ? refs : [...refs, rel]
}

/** Freie Bilder der Bibliothek, neueste zuerst. */
export function freeImages(items: LibraryItem[]): LibraryItem[] {
  return items.filter((i) => i.source === "studio_free" && i.kind === "image").sort((a, b) => b.created_at.localeCompare(a.created_at))
}

/** Alle Shots als Auswahl „Szene · Shot N“; Wert „Szene:Shot“. */
export function shotChoices(plan: Plan | null): { value: string; scene: string; n: number }[] {
  return (plan?.scenes ?? []).flatMap((s) => s.shots.map((sh, i) => ({ value: `${s.id}:${sh.id}`, scene: s.title, n: i + 1 })))
}
