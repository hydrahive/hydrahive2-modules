// Ghostwriter G2 – Server-Aufrufe für Lauf, Gliederung und abgelegte Vorschläge (Spec ghostwriter.md §9).
import { storyBase, StoryApiError, authHeader, errorFrom, type ServerScene, type ServerStructure } from "./api"
import type { Outline } from "./outlineModel"
import type { RunInfo } from "./runView"

export type RunScope = "chapter" | "from" | "book"
export interface RunRequest {
  scope: RunScope; chapter_id?: string; scene_id?: string; skip_filled: boolean; length_words?: number
  /** Quelle: Gliederung/Zusammenfassungen (Standard) oder Interview (G3, nur Kapitel). */
  source?: "outline" | "interview"
}
export interface RunEstimate {
  scenes: number; skipped_filled: number; skipped_no_summary: number; input_tokens: number; output_tokens: number
  model: string; cost_micros: number | null; limit_tokens: number
}

async function call<T>(pid: string, bid: string, method: string, path: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${storyBase(pid, bid)}${path}`, {
      method, headers: { "Content-Type": "application/json", ...authHeader() },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (e) {
    throw new StoryApiError(0, "network", undefined, String(e))
  }
  if (!res.ok) throw await errorFrom(res)
  return (await res.json()) as T
}

const query = (r: RunRequest) => new URLSearchParams(Object.entries({
  scope: r.scope, chapter_id: r.chapter_id ?? "", scene_id: r.scene_id ?? "", skip_filled: String(r.skip_filled),
  length_words: r.length_words ? String(r.length_words) : "", source: r.source ?? "",
}).filter(([, v]) => v !== "")).toString()

export const runApi = {
  estimate: (pid: string, bid: string, r: RunRequest) => call<RunEstimate>(pid, bid, "GET", `/ghost/run/estimate?${query(r)}`),
  start: (pid: string, bid: string, r: RunRequest, overLimit: boolean) =>
    call<RunInfo>(pid, bid, "POST", "/ghost/run", { ...r, confirm: true, confirm_over_limit: overLimit }),
  get: (pid: string, bid: string) => call<RunInfo | null>(pid, bid, "GET", "/ghost/run"),
  cancel: (pid: string, bid: string) => call<{ ok: boolean }>(pid, bid, "POST", "/ghost/run/cancel"),
  outline: (pid: string, bid: string, f: { idea: string; hints: string; chapters: number; scenes_per_chapter: number }) =>
    call<Outline>(pid, bid, "POST", "/ghost/outline", f),
  applyOutline: (pid: string, bid: string, outline: Outline, baseVersion: number) =>
    call<{ structure: ServerStructure; scenes: Record<string, ServerScene> }>(pid, bid, "POST", "/ghost/outline/apply",
      { outline, base_version: baseVersion }),
  proposal: (pid: string, bid: string, sid: string) =>
    call<{ text: string; words: number; model: string; at: string }>(pid, bid, "GET", `/proposals/${encodeURIComponent(sid)}`),
  acceptProposal: (pid: string, bid: string, sid: string, baseVersion: number) =>
    call<ServerScene>(pid, bid, "POST", `/proposals/${encodeURIComponent(sid)}/accept`, { base_version: baseVersion }),
  scene: (pid: string, bid: string, sid: string) => call<ServerScene>(pid, bid, "GET", `/scenes/${encodeURIComponent(sid)}`),
  discardProposal: (pid: string, bid: string, sid: string) =>
    call<{ ok: boolean }>(pid, bid, "DELETE", `/proposals/${encodeURIComponent(sid)}`),
}
