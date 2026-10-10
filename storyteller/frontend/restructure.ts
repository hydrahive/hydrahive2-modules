// C2 – Umbau-Vorschlag des Autors und Schalter „Autor darf die Gliederung direkt ändern“
// (Spec autor-gliederung-c2.md §2b): Aufrufe + reine Hilfen ohne React (restructure.test.ts).
import { call, type ServerScene, type ServerStructure } from "./api"
import type { AgentStructure, Book, GhostSettings } from "./model"

/** Offener Umbau-Vorschlag (genau einer je Buch). ``lines``: Schritte in Klartext; before/after: Kapiteltitel. */
export interface RestructureProposal {
  steps: unknown[]; lines: string[]; before: string[]; after: string[]; base_structure_version: number
  source: "agent"; author: string; note: string; session_id: string; at: string
  replaced_from?: { author: string; at: string } | null
}
export interface RestructureResult { structure: ServerStructure; scenes: ServerScene[]; ids: unknown; lines: string[] }

const path = (pid: string, bid: string) =>
  `/projects/${encodeURIComponent(pid)}/books/${encodeURIComponent(bid)}/proposals/restructure`

export const restructureApi = {
  get: (pid: string, bid: string) => call<RestructureProposal | null>("GET", path(pid, bid)),
  accept: (pid: string, bid: string) => call<RestructureResult>("POST", `${path(pid, bid)}/accept`),
  discard: (pid: string, bid: string) => call<{ ok: boolean }>("DELETE", path(pid, bid)),
}

/** Schalter je Buch: alles außer „direct“ gilt als Vorschlag (Standard). */
export function agentStructure(g: GhostSettings): AgentStructure {
  return g.agent_structure === "direct" ? "direct" : "propose"
}

export function withAgentStructure(b: Book, direct: boolean): Book {
  return { ...b, ghost: { ...b.ghost, agent_structure: direct ? "direct" : "propose" } }
}

export interface ChapterDiff { after: { title: string; kind: "new" | "same" }[]; gone: string[] }

/** Vorher/Nachher nach Kapiteltitel: im Nachher neu oder geblieben; weggefallen = vorher da, nachher nicht. */
export function chapterDiff(before: string[], after: string[]): ChapterDiff {
  const had = new Set(before)
  const has = new Set(after)
  return { after: after.map((title) => ({ title, kind: had.has(title) ? "same" : "new" })),
           gone: before.filter((title) => !has.has(title)) }
}

/** Hat der Autor die Gliederung direkt geändert? Neu holen nur ohne Ungespeichertes (sonst Konflikt-Dialog). */
export function needsStructureReload(local: number, server: number, dirty: boolean): boolean {
  return !dirty && server > local
}
