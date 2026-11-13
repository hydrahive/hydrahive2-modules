/** Reine Hilfen der TV-Werkstatt (ohne React), damit sie einzeln testbar sind. */

/** Fehlercode aus einer Antwort des Servers oder aus dem Zustand → Schlüssel für die Texte (unbekannt → allgemein). */
export function errorKey(e: unknown): string {
  const code = typeof e === "string" ? e
    : typeof e === "object" && e !== null
      ? ((e as { code?: unknown }).code ?? (e as { detail?: { code?: unknown } }).detail?.code)
      : undefined
  return typeof code === "string" && /^tvw_[a-z_]+$/.test(code) ? `err.${code}` : "err.general"
}

/** Kurzzeile unter dem Gerätenamen: „Modell · Android N“, fehlende Teile fallen weg. */
export function deviceLine(d: { model?: string; android?: string }): string {
  const parts = [d.model ?? "", d.android ? `Android ${d.android}` : ""].filter(Boolean)
  return parts.join(" · ")
}
