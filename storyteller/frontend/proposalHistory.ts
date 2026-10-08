// A2 – Verlauf ersetzter/verworfener Vorschläge (Spec nichts-geht-verloren.md §2): Aufrufe + reine Hilfen.
import { call } from "./api"
import type { InfoProposal } from "./infoProposal"
import type { ProposalInfo } from "./api"

export type HistoryKind = "text" | "info"

export interface HistoryEntry {
  id: string; kind: HistoryKind; at: string; source: "run" | "agent"; author: string; note: string; model: string
  reason: "replaced" | "discarded"; replaced_by: string; replaced_at: string
  words?: number; fields?: Record<string, string>
}

/** Herkunft lesbar: Agent-Name ohne Buchtitel („Buch — Lektor“ → „Lektor“), sonst Lauf/Agent. */
export function originLabel(e: { author?: string; source?: string }, t: (k: string) => string): string {
  const a = (e.author ?? "").trim()
  if (a) return a.includes("—") ? a.split("—").pop()!.trim() : a
  return e.source === "agent" ? t("history_from_agent") : t("history_from_run")
}

/** Wer ersetzt wurde – aus der Antwort beim Ablegen bzw. dem Fortschritt eines Laufs. */
export interface ReplacedFrom { source: string; author: string; at: string }

const path = (pid: string, bid: string, sid: string) =>
  `/projects/${encodeURIComponent(pid)}/books/${encodeURIComponent(bid)}/scenes/${encodeURIComponent(sid)}/proposal-history`

export const historyApi = {
  list: (pid: string, bid: string, sid: string) => call<HistoryEntry[]>("GET", path(pid, bid, sid)),
  get: (pid: string, bid: string, sid: string, kind: HistoryKind, id: string) =>
    call<HistoryEntry & { text?: string }>("GET", `${path(pid, bid, sid)}/${kind}/${encodeURIComponent(id)}`),
  restore: <K extends HistoryKind>(pid: string, bid: string, sid: string, kind: K, id: string) =>
    call<K extends "text" ? ProposalInfo & { text: string } : InfoProposal>(
      "POST", `${path(pid, bid, sid)}/${kind}/${encodeURIComponent(id)}/restore`),
}
