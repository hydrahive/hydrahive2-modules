/** Reine Hilfsfunktionen der Sammlung (Spec §12.2) – ohne React, gut zu testen. */

export const BASE = "/modules/diagramme"
const KINDS = new Set(["architecture", "workflow", "sequence", "dataflow", "lifecycle", "erd", "class", "tree",
  "timeline", "waterfall", "explainer"])
const ERR = new Set(["diagram_not_found", "diagram_not_owner", "diagram_not_in_trash", "diagram_kind_unknown",
  "diagram_input_too_large", "diagram_invalid", "diagram_timeout", "diagram_node_missing", "diagram_failed",
  "diagram_repo_outside"])

export interface Filter { q: string; project: string; trash: boolean }

export function listQuery(f: Filter): string {
  const p = new URLSearchParams({ trash: f.trash ? "1" : "0" })
  if (f.q.trim()) p.set("q", f.q.trim())
  if (f.project) p.set("project", f.project)
  return `${BASE}/list?${p.toString()}`
}

export function kindLabelKey(kind: string): string {
  return `kind.${KINDS.has(kind) ? kind : "other"}`
}

export function errorKey(e: unknown): string {
  const code = typeof e === "object" && e !== null ? (e as { code?: unknown }).code : undefined
  return typeof code === "string" && ERR.has(code) ? `err.${code}` : "err.general"
}

export function shortDate(iso: string): string {
  if (!iso) return ""
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}, ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function sameUser(item: { username: string }, username: string | null | undefined, role: string | null | undefined) {
  return role === "admin" || item.username === username
}
