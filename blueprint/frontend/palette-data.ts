/**
 * Baustein-Palette: alle verfügbaren Node-Typen, gruppiert in Layout (Seiten-
 * Design) und Flow (Funktionsplan). Jeder Eintrag definiert subtype, Anzeige-
 * Label, lucide-Icon-Name und ob ein Platzhalter-Feld sinnvoll ist.
 *
 * Client-seitig definiert (kein Backend) — das Board ist reines Skizzen-Werkzeug,
 * die Bedeutung interpretiert der Agent beim Lesen.
 */
export interface PaletteItem {
  subtype: string
  label: string
  icon: string
  hasPlaceholder?: boolean
}

export interface PaletteGroup {
  kind: "layout" | "flow"
  label: string
  items: PaletteItem[]
}

export const PALETTE: PaletteGroup[] = [
  {
    kind: "layout",
    label: "Layout",
    items: [
      { subtype: "page", label: "Seite", icon: "Layout" },
      { subtype: "card", label: "Karte / Box", icon: "Square" },
      { subtype: "menu_item", label: "Menü-Eintrag", icon: "Menu" },
      { subtype: "button", label: "Button", icon: "MousePointerClick" },
      { subtype: "input", label: "Eingabefeld", icon: "TextCursorInput", hasPlaceholder: true },
      { subtype: "toggle", label: "Schalter", icon: "ToggleLeft" },
      { subtype: "heading", label: "Überschrift", icon: "Heading" },
      { subtype: "list", label: "Liste / Tabelle", icon: "List" },
    ],
  },
  {
    kind: "flow",
    label: "Funktion",
    items: [
      { subtype: "event", label: "Event (Klick…)", icon: "Zap" },
      { subtype: "action", label: "Aktion", icon: "Play" },
      { subtype: "datasource", label: "Datenquelle", icon: "Database" },
      { subtype: "condition", label: "Bedingung", icon: "GitBranch" },
      { subtype: "display", label: "Anzeige", icon: "Eye" },
      { subtype: "note", label: "Notiz", icon: "StickyNote" },
    ],
  },
]

// subtype → kind, für schnelles Nachschlagen.
const KIND_OF: Record<string, "layout" | "flow"> = Object.fromEntries(
  PALETTE.flatMap((g) => g.items.map((it) => [it.subtype, g.kind])),
)

export function kindOf(subtype: string): "layout" | "flow" {
  return KIND_OF[subtype] ?? "layout"
}

export function labelOf(subtype: string): string {
  for (const g of PALETTE) {
    const it = g.items.find((i) => i.subtype === subtype)
    if (it) return it.label
  }
  return subtype
}

export function iconOf(subtype: string): string {
  for (const g of PALETTE) {
    const it = g.items.find((i) => i.subtype === subtype)
    if (it) return it.icon
  }
  return "Square"
}

export function hasPlaceholder(subtype: string): boolean {
  for (const g of PALETTE) {
    const it = g.items.find((i) => i.subtype === subtype)
    if (it) return Boolean(it.hasPlaceholder)
  }
  return false
}
