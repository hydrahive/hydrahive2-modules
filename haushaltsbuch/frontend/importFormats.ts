// Import-Formate (V9 Phase 2): Beschriftungen, Hinweise und laienverständliche Fehlermeldungen.
import type { ImportFormat, StoredImportFormat } from "./types"

export const FORMAT_OPTIONS: { value: ImportFormat; label: string }[] = [
  { value: "auto", label: "Automatisch erkennen" },
  { value: "camt", label: "CAMT V2/V8 (XML)" },
  { value: "mt940", label: "MT940" },
  { value: "csv", label: "CSV" },
  { value: "pdf", label: "PDF-Kontoauszug" },
  { value: "paypal", label: "PayPal-Export (CSV)" },
]

export const FORMAT_HINTS: Partial<Record<ImportFormat, string>> = {
  pdf: "Nur Kontoauszüge, die Text enthalten (zum Markieren und Kopieren). Eingescannte PDFs lade bitte über die Beleg-Erkennung hoch. Unklare Zeilen werden markiert, nicht geraten – du prüfst alles, bevor gebucht wird.",
  paypal: "Der Aktivitäten-Export aus deinem PayPal-Konto (CSV). Gebühren erscheinen als eigene Zeile, Währungsumrechnungen werden ausgeblendet.",
}

const SOURCE_LABELS: Partial<Record<StoredImportFormat, string>> = { pdf: "PDF", paypal: "PayPal" }
/** Kurzname des Quellformats für Listen und Kopfzeilen („PDF“, „PayPal“, sonst z. B. „CAMT“). */
export const sourceFormatLabel = (format: StoredImportFormat): string => SOURCE_LABELS[format] ?? format.toUpperCase()

/** Dateiendungen, die der Dateiwähler anbietet. */
export const UPLOAD_ACCEPT = ".xml,.mt940,.sta,.txt,.csv,.pdf,text/csv,application/xml,text/xml,application/pdf"

/** CSV-Zuordnung nur bei CSV – nie bei PDF/PayPal; bei „Automatisch“ nur für .csv-Dateien. */
export function needsCsvMapping(format: ImportFormat, fileName?: string): boolean {
  if (format === "csv") return true
  return format === "auto" && Boolean(fileName?.toLowerCase().endsWith(".csv"))
}

export const IMPORT_MESSAGES: Record<string, string> = {
  pdf_no_text_layer: "Dieses PDF enthält keinen lesbaren Text (eingescannt). Bitte als Beleg über die Beleg-Erkennung hochladen oder einen CSV-/CAMT-Export deiner Bank verwenden.",
  pdf_unreadable: "Das PDF lässt sich nicht lesen. Es ist vermutlich beschädigt oder passwortgeschützt. Lade den Kontoauszug bitte noch einmal ohne Passwortschutz bei deiner Bank herunter.",
  pdf_too_many_pages: "Das PDF hat mehr als 50 Seiten. Bitte teile den Kontoauszug in kürzere Zeiträume auf.",
  pdf_no_transactions: "In diesem PDF wurde keine Buchungszeile erkannt. Prüfe, ob es wirklich ein Kontoauszug ist, oder nutze einen CSV-/CAMT-Export deiner Bank.",
  pdf_extraction_unavailable: "Das Auslesen von PDFs ist auf diesem Server gerade nicht verfügbar. Bitte nutze vorerst einen CSV- oder CAMT-Export oder wende dich an die Administration.",
  paypal_header_invalid: "Das ist kein gültiger PayPal-Aktivitäten-Export: Pflichtspalten fehlen. Exportiere die Aktivitäten in PayPal erneut als CSV mit allen Spalten.",
  pdf_line_ambiguous: "Datum oder Betrag dieser Zeile sind im PDF nicht eindeutig. Bitte mit dem Kontoauszug vergleichen und die Zeile von Hand korrigieren oder verwerfen.",
  paypal_status_not_completed: "Diese PayPal-Zahlung ist noch nicht abgeschlossen (z. B. ausstehend oder abgelehnt). Sie kann erst importiert werden, wenn sie abgeschlossen ist.",
  possible_duplicate: "Mögliches Duplikat (schwacher Treffer)",
  account_currency_mismatch: "Währung passt nicht zum Zielkonto",
}

/** Meldung zu einem Fehlercode; unbekannte Codes bleiben lesbar („foo_bar“ → „foo bar“). */
export const importMessage = (code: string): string => IMPORT_MESSAGES[code] ?? code.replaceAll("_", " ")

/** Fehlertext fürs Upload-Formular: bekannte Import-Codes übersetzen, sonst die normale Meldung. */
export function importErrorText(error: unknown, fallback: (error: unknown) => string): string {
  if (error instanceof Error) {
    const code = (error as Error & { code?: string }).code
    if (code && IMPORT_MESSAGES[code]) return IMPORT_MESSAGES[code]
    if (IMPORT_MESSAGES[error.message]) return IMPORT_MESSAGES[error.message]
  }
  return fallback(error)
}
