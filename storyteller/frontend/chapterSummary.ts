// A5c – Kapitel-Zusammenfassung (Spec ki-qualitaet-a5.md §2c): Aufrufe + reine Hilfen.
// Eigene Ablage (chapters.json), nicht in der Gliederung – toStructure würde ein Feld dort beim Speichern verwerfen.
import { call } from "./api"

export interface ChapterSummary { summary: string; version: number; updated_at: string }

const base = (pid: string, bid: string) =>
  `/projects/${encodeURIComponent(pid)}/books/${encodeURIComponent(bid)}/chapter-summaries`

export const chapterSummaryApi = {
  all: (pid: string, bid: string) => call<{ chapters: Record<string, ChapterSummary> }>("GET", base(pid, bid)),
  save: (pid: string, bid: string, cid: string, summary: string, baseVersion: number) =>
    call<ChapterSummary>("PUT", `${base(pid, bid)}/${encodeURIComponent(cid)}`, { summary, base_version: baseVersion }),
  generate: (pid: string, bid: string, cid: string, model?: string) =>
    call<{ summary: string }>("POST", `${base(pid, bid)}/${encodeURIComponent(cid)}/generate`, model ? { model } : {}),
}

/** Ist ungespeicherte Arbeit da? (Text weicht vom gespeicherten Stand ab – Leerraum am Rand zählt nicht.) */
export function isDirty(draft: string, saved: string): boolean {
  return draft.trim() !== saved.trim()
}
