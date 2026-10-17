/** Tastenkürzel des Studios (Spec „Tastenkürzel“). Reine Daten + Zuordnung, damit testbar. */

export type ShortcutAction =
  | "toggle-play" | "seek-back" | "seek-forward" | "frame-back" | "frame-forward" | "jump-back" | "jump-forward"
  | "goto-start" | "goto-end" | "split" | "split-left" | "split-right" | "delete" | "copy" | "paste" | "duplicate"
  | "toggle-snap" | "marker" | "undo" | "redo" | "command" | "help"

export interface Shortcut {
  action: ShortcutAction
  keys: string[]
}

export const SHORTCUTS: Shortcut[] = [
  { action: "toggle-play", keys: ["space", "k"] },
  { action: "seek-back", keys: ["j"] },
  { action: "seek-forward", keys: ["l"] },
  { action: "frame-back", keys: ["arrowleft"] },
  { action: "frame-forward", keys: ["arrowright"] },
  { action: "jump-back", keys: ["shift+arrowleft"] },
  { action: "jump-forward", keys: ["shift+arrowright"] },
  { action: "goto-start", keys: ["home"] },
  { action: "goto-end", keys: ["end"] },
  { action: "split", keys: ["s"] },
  { action: "split-left", keys: ["q"] },
  { action: "split-right", keys: ["w"] },
  { action: "delete", keys: ["delete", "backspace"] },
  { action: "copy", keys: ["ctrl+c"] },
  { action: "paste", keys: ["ctrl+v"] },
  { action: "duplicate", keys: ["ctrl+d"] },
  { action: "toggle-snap", keys: ["n"] },
  { action: "marker", keys: ["m"] },
  { action: "undo", keys: ["ctrl+z"] },
  { action: "redo", keys: ["ctrl+shift+z", "ctrl+y"] },
  { action: "command", keys: ["ctrl+k"] },
  { action: "help", keys: ["shift+?", "?"] },
]

const BY_KEY = new Map(SHORTCUTS.flatMap((s) => s.keys.map((k) => [k, s.action] as const)))

interface KeyLike {
  key: string
  ctrlKey: boolean
  metaKey: boolean
  shiftKey: boolean
  altKey: boolean
}

/** Taste als Name wie in SHORTCUTS („ctrl+shift+z“). Cmd (Mac) zählt wie Strg. */
export function keyName(e: KeyLike): string {
  const key = e.key === " " ? "space" : e.key.toLowerCase()
  const parts = [(e.ctrlKey || e.metaKey) && "ctrl", e.altKey && "alt", e.shiftKey && key !== "?" && "shift", key]
  return parts.filter(Boolean).join("+")
}

/** Welche Aktion zur Taste gehört – oder null. In Eingabefeldern wirkt kein Kürzel. */
export function actionFor(e: KeyLike, target: EventTarget | null): ShortcutAction | null {
  const el = target as HTMLElement | null
  const tag = el?.tagName?.toLowerCase()
  if (tag === "input" || tag === "textarea" || tag === "select" || el?.isContentEditable) return null
  return BY_KEY.get(keyName(e)) ?? null
}

/** Anzeige einer Taste für Menschen („Strg+Shift+Z“). */
export function keyLabel(key: string): string {
  const names: Record<string, string> = {
    ctrl: "Strg", shift: "Shift", alt: "Alt", space: "Leertaste", arrowleft: "←", arrowright: "→",
    home: "Pos1", end: "Ende", delete: "Entf", backspace: "⌫",
  }
  return key.split("+").map((p) => names[p] ?? p.toUpperCase()).join(" + ")
}
