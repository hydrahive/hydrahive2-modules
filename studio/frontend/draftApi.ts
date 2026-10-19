import { api } from "@/shared/api-client"
import type { ElementKind } from "./planApi"

/** Drehbuch-Entwurf (Backend: backend/_draft.py, Spec „Bauplan B2“). Wird nur gezeigt, erst „Übernehmen“ speichert. */
export interface DraftShot { shot: string; prompt: string; element_keys: string[]; duration: number }
export interface DraftScene {
  title: string
  description: string
  location: string
  time_of_day: string
  element_keys: string[]
  shots: DraftShot[]
}
export interface DraftElement { key: string; kind: ElementKind; name: string; description: string }
export interface Draft {
  head: { title: string; logline: string; description: string; style: string }
  elements: DraftElement[]
  scenes: DraftScene[]
}
export interface DraftBook { id: string; title: string; entities: number; chapters: { id: string; title: string; scenes: number }[] }
export interface ApplyResult { mode: "new" | "append" | "replace"; scenes: number; shots: number; elements_new: number; elements_reused: number }
export type IdeaLength = "30" | "60" | "120"
export const IDEA_LENGTHS: IdeaLength[] = ["30", "60", "120"]

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}/plan/draft`

export const draftApi = {
  idea: (pid: string, idea: string, length: IdeaLength, style: string) =>
    api.post<{ draft: Draft }>(`${base(pid)}/idea`, { idea, length, style }),
  books: (pid: string) => api.get<{ books: DraftBook[] }>(`${base(pid)}/books`),
  book: (pid: string, book_id: string, chapter_ids: string[]) =>
    api.post<{ draft: Draft; truncated: number }>(`${base(pid)}/book`, { book_id, chapter_ids }),
  apply: (pid: string, draft: Draft, replace = false) => api.post<ApplyResult>(`${base(pid)}/apply`, replace ? { draft, replace: true } : { draft }),
  /** G1: geführter Weg – ein Bild je Szene, mit Filmart */
  ideaGuided: (pid: string, body: { idea: string; length: IdeaLength; style: string; kind: string; shots_per_scene: 1 }) =>
    api.post<{ draft: Draft }>(`${base(pid)}/idea`, body),
}
