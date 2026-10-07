// Ghostwriter G4 – Chat mit dem Projekt-Agenten (Spec ghostwriter.md §11.3): Info, Sitzung anlegen,
// offene Vorschläge nachfragen, fehlende Storyteller-Werkzeuge zuschalten (nur Admin, Kern-Route).
import { authHeader, errorFrom, storyBase, StoryApiError, type ProposalInfo, type ServerScene, type ServerStructure } from "./api"
import type { EntityProposal } from "./entityProposal"
import type { Outline } from "./outlineModel"
import type { InfoProposal } from "./infoProposal"
import { markOf, type ProposalMark } from "./proposalMark"

/** G4d: offener Gliederungs-Vorschlag des Agenten (genau einer je Buch). */
export interface OutlineProposal { outline: Outline; base_structure_version: number; source: "run" | "agent"; session_id: string; note: string; at: string }

export interface ChatInfo { agent: { id: string; name: string } | null; tools_missing: string[]; can_start: boolean }
export interface ChatStart { session_id: string; url: string; intro: string; agent: { id: string; name: string }; reused?: boolean }

async function call<T>(url: string, method: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, { method, headers: { "Content-Type": "application/json", ...authHeader() },
      body: body === undefined ? undefined : JSON.stringify(body) })
  } catch (e) {
    throw new StoryApiError(0, "network", undefined, String(e))
  }
  if (!res.ok) throw await errorFrom(res)
  return (await res.json()) as T
}

/** Offene Vorschläge als Markierungen je Szene (Herkunft „agent“ oder „run“). */
export function proposalMarks(list: ProposalInfo[]): Record<string, ProposalMark> {
  const out: Record<string, ProposalMark> = {}
  for (const p of list) out[p.scene_id] = markOf(p)
  return out
}

/** Werkzeugliste des Agenten um die fehlenden ergänzen (Reihenfolge bleibt, nichts doppelt). */
export function withTools(have: string[], missing: string[]): string[] {
  return [...have, ...missing.filter((n) => !have.includes(n))]
}

export const chatApi = {
  info: (pid: string, bid: string) => call<ChatInfo>(`${storyBase(pid, bid)}/chat`, "GET"),
  /** reuse (G4e): jüngste eigene Sitzung dieses Buchs weiternutzen statt eine neue anzulegen. */
  start: (pid: string, bid: string, sceneId: string, reuse = false) =>
    call<ChatStart>(`${storyBase(pid, bid)}/chat`, "POST", { scene_id: sceneId, reuse }),
  proposals: (pid: string, bid: string) => call<ProposalInfo[]>(`${storyBase(pid, bid)}/proposals`, "GET"),
  outlineProposal: async (pid: string, bid: string): Promise<OutlineProposal | null> => {
    try { return await call<OutlineProposal>(`${storyBase(pid, bid)}/proposals/outline`, "GET") }
    catch (e) { if (e instanceof StoryApiError && e.status === 404) return null; throw e }
  },
  acceptOutline: (pid: string, bid: string, outline: Outline, baseVersion: number) =>
    call<{ structure: ServerStructure; scenes: Record<string, ServerScene> }>(`${storyBase(pid, bid)}/proposals/outline/accept`, "POST",
      { outline, base_version: baseVersion }),
  discardOutline: (pid: string, bid: string) => call<{ ok: boolean }>(`${storyBase(pid, bid)}/proposals/outline`, "DELETE"),
  entityProposals: (pid: string, bid: string) => call<EntityProposal[]>(`${storyBase(pid, bid)}/proposals/entities`, "GET"),
  acceptEntity: (pid: string, bid: string, id: string, baseVersion: number) =>
    call<ServerStructure>(`${storyBase(pid, bid)}/proposals/entities/${encodeURIComponent(id)}/accept`, "POST", { base_version: baseVersion }),
  discardEntity: (pid: string, bid: string, id: string) =>
    call<{ ok: boolean }>(`${storyBase(pid, bid)}/proposals/entities/${encodeURIComponent(id)}`, "DELETE"),
  infoProposals: (pid: string, bid: string) => call<InfoProposal[]>(`${storyBase(pid, bid)}/proposals/info`, "GET"),
  acceptInfo: (pid: string, bid: string, sid: string, baseVersion: number, fields: string[]) =>
    call<ServerScene>(`${storyBase(pid, bid)}/proposals/${encodeURIComponent(sid)}/info/accept`, "POST", { base_version: baseVersion, fields }),
  discardInfo: (pid: string, bid: string, sid: string) =>
    call<{ ok: boolean }>(`${storyBase(pid, bid)}/proposals/${encodeURIComponent(sid)}/info`, "DELETE"),
  /** Nur Admin: Kern GET/PATCH /api/agents/{id}. */
  addTools: async (agentId: string, missing: string[]) => {
    const agent = await call<{ tools?: string[] }>(`/api/agents/${encodeURIComponent(agentId)}`, "GET")
    return call<{ tools: string[] }>(`/api/agents/${encodeURIComponent(agentId)}`, "PATCH", { tools: withTools(agent.tools ?? [], missing) })
  },
}
