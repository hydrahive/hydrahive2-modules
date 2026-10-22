/** Reine Logik der Mailliste: Mehrfachauswahl und Tastenkürzel (Spec §6). Testbar ohne DOM. */

export function toggle(sel: Set<number>, id: number): Set<number> {
  const out = new Set(sel)
  if (out.has(id)) out.delete(id)
  else out.add(id)
  return out
}

/** Alle sichtbaren an – außer es sind schon alle an, dann alle aus. */
export function toggleAll(sel: Set<number>, ids: number[]): Set<number> {
  return ids.length > 0 && ids.every((id) => sel.has(id)) ? new Set() : new Set(ids)
}

interface Flagged { id: number; seen: number; flagged: number; deleted_on_server: number }

export function selectionFlags(items: Flagged[], sel: Set<number>) {
  const chosen = items.filter((m) => sel.has(m.id))
  return {
    anyUnseen: chosen.some((m) => !m.seen),
    anyUnflagged: chosen.some((m) => !m.flagged),
    onServer: chosen.filter((m) => m.deleted_on_server !== 1).length,
  }
}

export function nextId(ids: number[], current: number | null, step: 1 | -1): number | null {
  if (ids.length === 0) return null
  const i = current == null ? -1 : ids.indexOf(current)
  if (i < 0) return ids[0]
  return ids[Math.min(ids.length - 1, Math.max(0, i + step))]
}

export type KeyAction = "next" | "prev" | "reply" | "reply_all" | "forward" | "archive" | "delete" | "search" | "compose"

const KEYS: Record<string, KeyAction> = {
  j: "next", k: "prev", r: "reply", a: "reply_all", f: "forward", e: "archive", "#": "delete", "/": "search", c: "compose",
}

interface KeyLike {
  key: string
  ctrlKey: boolean
  metaKey: boolean
  altKey: boolean
  target: { tagName?: string; isContentEditable?: boolean } | null
}

/** Taste → Aktion. Nie beim Tippen in Feldern und nie mit Strg/Cmd/Alt (sonst kollidiert es mit Browser-Kürzeln). */
export function keyAction(e: KeyLike): KeyAction | null {
  if (e.ctrlKey || e.metaKey || e.altKey) return null
  const t = e.target
  if (t && (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName ?? ""))) return null
  return KEYS[e.key] ?? null
}
