// Reine Hilfsfunktionen für Fälle (vitest) – keine React-/API-Abhängigkeit.

export type Light = "red" | "yellow" | "green" | "none"

export const PARTY_ROLES: Record<string, string> = {
  opponent: "Gegenseite",
  lawyer: "Anwalt/Anwältin",
  authority: "Behörde",
  court: "Gericht",
  witness: "Zeuge/Zeugin",
  me: "Ich / wir",
  other: "Sonstige",
}

export const CASE_STATUS: Record<string, string> = { open: "offen", waiting: "wartet", done: "erledigt" }

export const KIND_LABEL: Record<string, string> = {
  days: "Tage", weeks: "Wochen", months: "Monate", years: "Jahre", date: "bestimmter Tag",
}

export function partyRoleLabel(role: string): string {
  return PARTY_ROLES[role] ?? role
}

/** Kalendertage von heute (lokal) bis zum ISO-Datum; negativ = vorbei. */
export function daysUntil(iso: string, today: Date = new Date()): number {
  const [y, m, d] = iso.split("-").map(Number)
  const due = Date.UTC(y, m - 1, d)
  const now = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())
  return Math.round((due - now) / 86_400_000)
}

/** Ampel: rot = überschritten oder ≤ 3 Tage, gelb = ≤ 14 Tage, grün = später; erledigte/keine Frist = none. */
export function deadlineLight(d: { due_date: string; status: string } | null | undefined, today: Date = new Date()): Light {
  if (!d || d.status !== "open") return "none"
  const n = daysUntil(d.due_date, today)
  if (n <= 3) return "red"
  if (n <= 14) return "yellow"
  return "green"
}

export function nextOpenDeadline<T extends { due_date: string; status: string }>(list: T[]): T | null {
  return list.filter((d) => d.status === "open").sort((a, b) => a.due_date.localeCompare(b.due_date))[0] ?? null
}

/** Text zur Ampel: „in 3 Tagen“, „heute“, „seit 2 Tagen vorbei“. */
export function dueText(iso: string, today: Date = new Date()): string {
  const n = daysUntil(iso, today)
  if (n === 0) return "heute"
  if (n === 1) return "morgen"
  if (n > 1) return `in ${n} Tagen`
  return n === -1 ? "seit gestern vorbei" : `seit ${-n} Tagen vorbei`
}

/** Prüfung des Aufnahmeformulars (Pflichtfelder Titel + Bundesland; Modell nur, wenn der Standard nicht nutzbar ist). */
export function caseFormErrors(f: { title: string; state: string }, model?: { mustChoose: boolean }): Record<string, string> {
  const out: Record<string, string> = {}
  const title = f.title.trim()
  if (!title) out.title = "Bitte einen kurzen Titel angeben."
  else if (title.length > 200) out.title = "Höchstens 200 Zeichen."
  if (!f.state) out.state = "Bitte das Bundesland wählen (für Feiertage bei Fristen)."
  if (model?.mustChoose) out.model = "Bitte ein Modell für den Rechts-Agenten wählen."
  return out
}

/** Modell des Rechts-Agenten (Fund hydratest 20.10.: Standard nicht im Katalog → „Neuer Fall“ scheiterte mit 400 ohne
 * Ausweg). `catalog` aus GET /llm/models?modality=chat: `selected` = Standard, wie er in der Liste heißt (leer, wenn er
 * dort fehlt). Eigene Wahl gewinnt. Ohne Katalog (Laden fehlgeschlagen) nicht blockieren – der Server prüft ohnehin. */
export function modelState(
  catalog: { standard: string; selected: string; ids: string[] } | null,
  chosen: string,
): { effective: string; mustChoose: boolean; warning: string | null } {
  if (chosen) return { effective: chosen, mustChoose: false, warning: null }
  if (!catalog) return { effective: "", mustChoose: false, warning: null }
  if (catalog.selected && catalog.ids.includes(catalog.selected)) {
    return { effective: catalog.selected, mustChoose: false, warning: null }
  }
  const warning = catalog.standard
    ? `Das Standard-Modell „${catalog.standard}“ ist gerade nicht verfügbar – bitte ein anderes wählen.`
    : "Es ist kein Standard-Modell eingestellt – bitte ein Modell wählen."
  return { effective: "", mustChoose: true, warning }
}

/** Fehlercode des Backends ({detail:{code}}) in einen verständlichen Satz. */
export function errorText(e: unknown): string {
  const code = (e as { detail?: { code?: string } })?.detail?.code ?? (e as { code?: string })?.code
  const map: Record<string, string> = {
    legal_case_not_found: "Fall nicht gefunden oder kein Zugriff.",
    legal_case_read_only: "Nur Leserechte in diesem Fall.",
    capability_denied: "Dafür fehlt die Freigabe „Recht: Fälle anlegen“.",
    legal_no_model: "Kein Standard-Modell eingestellt – bitte unten ein Modell wählen.",
    legal_model_unavailable: "Dieses Modell ist nicht verfügbar – bitte unten ein anderes Modell wählen.",
    legal_event_date_invalid: "Bitte ein gültiges Datum angeben.",
    legal_deadline_invalid: "Diese Frist lässt sich so nicht rechnen (Art/Anzahl prüfen).",
    legal_proposal_decided: "Über diesen Vorschlag wurde schon entschieden.",
    legal_field_required: "Pflichtfeld fehlt.",
    legal_role_invalid: "Bitte eine Rolle wählen.",
  }
  if (code && map[code]) return map[code]
  return String((e as Error)?.message ?? e)
}
