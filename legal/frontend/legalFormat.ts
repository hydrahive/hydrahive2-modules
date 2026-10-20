// Reine Hilfsfunktionen (vitest) – keine React-/API-Abhängigkeit.

export interface LawItem {
  key: string
  abbr: string
  title: string
  stand: string
  fetched_at: string
  pinned: boolean
  norms: number
  group: string | null
}

/** Gesetze nach Rubrik der Kernliste gruppieren; nachgeladene unter „Weitere“. Reihenfolge der Rubriken wie in der Spec. */
export function groupLaws(laws: LawItem[], groups: string[]): { group: string; laws: LawItem[] }[] {
  const out = groups.map((group) => ({ group, laws: laws.filter((l) => l.group === group) }))
  const other = laws.filter((l) => !l.group || !groups.includes(l.group))
  if (other.length) out.push({ group: "Weitere", laws: other })
  return out.filter((g) => g.laws.length > 0)
}

/** „§ 536c“ + „BGB“ → „§ 536c BGB“; „Art 3“ + „GG“ → „Art. 3 GG“ (wie das Backend, norm_view.citation_text). */
export function citationText(enbez: string, abbr: string): string {
  return `${enbez.replace(/^Art /, "Art. ")} ${abbr}`
}

/** Absätze „(1) …“, „(2) …“ und Listenpunkte „1. …“ als Zeilen; leere Zeilen weg. */
export function normLines(text: string): { kind: "para" | "item"; text: string }[] {
  return text
    .split("\n")
    .map((t) => t.trim())
    .filter(Boolean)
    .map((t) => ({ kind: /^(\d+|[a-z])\.\s/.test(t) ? "item" : "para", text: t }))
}

/** ISO-Zeitpunkt → „20.10.2026“ (ohne Uhrzeit, deutsch). Ungültig → Eingabe unverändert. */
export function shortDate(iso: string | null | undefined): string {
  if (!iso) return ""
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso)
  return m ? `${m[3]}.${m[2]}.${m[1]}` : iso
}

/** Abgleich-Status in einem Satz. */
export function syncSummary(last: { state: string; total: number; changed: number; errors: unknown[]; finished_at: string | null } | null, running: boolean): string {
  if (running || last?.state === "running") return "Abgleich läuft …"
  if (!last) return "Noch kein Abgleich – die Gesetze werden kurz nach dem Start geladen."
  const when = shortDate(last.finished_at)
  const err = last.errors.length ? `, ${last.errors.length} Fehler` : ""
  return `Letzter Abgleich ${when}: ${last.total} Gesetze, ${last.changed} geändert${err}.`
}
