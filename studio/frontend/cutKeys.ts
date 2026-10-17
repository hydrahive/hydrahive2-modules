/** Tastenkürzel → Bearbeitung der Zeitleiste (nur im Reiter „Schneiden“). */
import type { ShortcutAction } from "./shortcuts"

export type EditAction =
  | { kind: "split" } | { kind: "split-keep"; drop: "left" | "right" } | { kind: "delete" } | { kind: "duplicate" }
  | { kind: "copy" } | { kind: "paste" } | { kind: "undo" } | { kind: "redo" }

const MAP: Partial<Record<ShortcutAction, EditAction>> = {
  split: { kind: "split" },
  "split-left": { kind: "split-keep", drop: "left" },
  "split-right": { kind: "split-keep", drop: "right" },
  delete: { kind: "delete" },
  duplicate: { kind: "duplicate" },
  copy: { kind: "copy" },
  paste: { kind: "paste" },
  undo: { kind: "undo" },
  redo: { kind: "redo" },
}

export function editAction(a: ShortcutAction): EditAction | null {
  return MAP[a] ?? null
}
