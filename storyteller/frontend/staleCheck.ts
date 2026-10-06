// Passt die Stelle im Editor noch zum KI-Vorschlag? Sonst nicht blind ersetzen.
import type { Editor } from "@tiptap/react"
import type { Suggestion } from "./suggest"

export function isStale(ed: Editor | null, s: Suggestion): boolean {
  if (!ed) return true
  const size = ed.state.doc.content.size
  if (s.to > size || s.from > size) return true
  return s.action !== "continue" && ed.state.doc.textBetween(s.from, s.to, "\n") !== s.original
}
