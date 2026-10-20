// Reine Hilfsfunktionen für Briefe und Schriftverkehr (vitest) – keine React-/API-Abhängigkeit.

/** DIN 5008 Form B, Maße in mm. Quelle: falzmarke.com/din-5008 (abgerufen 20.10.2026), dort „mehrfach bestätigt“
 * (Wikimedia-Maßzeichnung Form B + Onlineprinters-Magazin). Der Abgleich mit dem kostenpflichtigen Normtext steht laut
 * Quelle aus. */
export const DIN = {
  headerMm: 45, addressLeftMm: 20, addressTextLeftMm: 25, addressWidthMm: 85, addressHeightMm: 45,
  returnMm: 5, notesMm: 12.7, recipientMm: 27.3, infoLeftMm: 125, infoWidthMm: 75, infoTopMm: 50,
  marginLeftMm: 25, marginRightMm: 20, foldMm: [105, 210], punchMm: 148.5, lineMm: 4.23,
}

export const DELIVERY_LABEL: Record<string, string> = {
  einwurf_einschreiben: "Einwurf-Einschreiben",
  einschreiben_rueckschein: "Einschreiben mit Rückschein",
  bote: "Bote",
  fax: "Fax (mit Sendebericht)",
  mail: "E-Mail",
  brief: "einfacher Brief",
  persoenlich: "persönlich übergeben",
}

const MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]

/** ISO „2026-10-20“ → „20. Oktober 2026“. Leer → leer, Unlesbares unverändert. */
export function deDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "")
  if (!m) return iso || ""
  const mon = MONTHS[Number(m[2]) - 1]
  return mon ? `${Number(m[3])}. ${mon} ${m[1]}` : iso
}

export interface CheckItem { key: string; ok: boolean; hint: string }
export interface CheckNorm { raw: string; citation: string; found: boolean }
export interface CheckResult { ok: boolean; items: CheckItem[]; norms: CheckNorm[] }

export function checkSummary(c: CheckResult | null): { open: number; total: number; badNorms: string[]; ok: boolean } {
  if (!c) return { open: 0, total: 0, badNorms: [], ok: false }
  return { open: c.items.filter((i) => !i.ok).length, total: c.items.length,
           badNorms: c.norms.filter((n) => !n.found).map((n) => n.citation), ok: c.ok }
}

export const CHECK_LABEL: Record<string, string> = {
  sender: "Absender mit Anschrift", recipient: "Empfänger mit Anschrift", date: "Datum", subject: "Betreff",
  reference: "Aktenzeichen", deadline_date: "Frist als Datum", deadline_future: "Frist liegt in der Zukunft",
  norms: "Normen belegt", delivery: "Zustellweg", attachments: "Anlagen",
}

/** Brieftext in Absätze (Leerzeile = neuer Absatz); [Platzhalter] je Absatz für die Markierung. */
export function splitBody(body: string): { text: string; placeholders: string[] }[] {
  return (body || "").split(/\n\s*\n/).map((t) => t.trim()).filter(Boolean)
    .map((text) => ({ text, placeholders: text.match(/\[[^\]\n]{1,120}\]/g) ?? [] }))
}

export function entryLabel(e: { direction: string; status: string; delivery: string; date: string }): string {
  if (e.direction === "in") return ["Eingang", deDate(e.date)].filter(Boolean).join(" · ")
  if (e.status === "draft") return "Ausgang · Entwurf"
  return ["Ausgang", `versendet ${deDate(e.date)}`, DELIVERY_LABEL[e.delivery] ?? e.delivery].filter(Boolean).join(" · ")
}
