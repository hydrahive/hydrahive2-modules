// Import-Formate (V9 Phase 2): Beschriftungen, Hinweise und laienverständliche Fehlermeldungen.
import { CRYPTO_MESSAGES, STALE_REASONS } from "./cryptoMessages"
import { IMPORT_FILE_MESSAGES, IMPORT_FLOW_MESSAGES, SPARKASSE_CSV_HINT } from "./importMessages"
import type { ImportFormat, StoredImportFormat } from "./types"

export const FORMAT_OPTIONS: { value: ImportFormat; label: string }[] = [
  { value: "auto", label: "Automatisch erkennen" },
  { value: "camt", label: "CAMT V2/V8 (XML)" },
  { value: "mt940", label: "MT940 (SWIFT, .sta/.txt)" },
  { value: "csv", label: "CSV" },
  { value: "pdf", label: "PDF-Kontoauszug" },
  { value: "paypal", label: "PayPal-Export (CSV)" },
]

export const FORMAT_HINTS: Partial<Record<ImportFormat, string>> = {
  pdf: "Nur Kontoauszüge, die Text enthalten (zum Markieren und Kopieren). Eingescannte PDFs lade bitte über die Beleg-Erkennung hoch. Unklare Zeilen werden markiert, nicht geraten – du prüfst alles, bevor gebucht wird.",
  auto: SPARKASSE_CSV_HINT + " Bekannte Banken werden ohne Spaltenzuordnung erkannt.",
  csv: SPARKASSE_CSV_HINT + " Für unbekannte Banken ordnest du die Spalten selbst zu.",
  mt940: "Nur echtes SWIFT-MT940 (.sta/.txt). " + SPARKASSE_CSV_HINT,
  paypal: "Der Aktivitäten-Export aus deinem PayPal-Konto (CSV). Gebühren erscheinen als eigene Zeile, Währungsumrechnungen werden ausgeblendet.",
}

const SOURCE_LABELS: Partial<Record<StoredImportFormat, string>> = { pdf: "PDF", paypal: "PayPal", crypto_trades: "Cryptoboard-Trades", crypto_ledger: "Cryptoboard-Ledger" }
/** Kurzname des Quellformats für Listen und Kopfzeilen („PDF“, „PayPal“, sonst z. B. „CAMT“). */
export const sourceFormatLabel = (format: StoredImportFormat): string => SOURCE_LABELS[format] ?? format.toUpperCase()

/** Dateiendungen, die der Dateiwähler anbietet. */
export const UPLOAD_ACCEPT = ".xml,.mt940,.sta,.txt,.csv,.pdf,text/csv,application/xml,text/xml,application/pdf"

/** CSV-Zuordnung vorab nur beim Format „CSV“. Bei „Automatisch“ wird direkt hochgeladen; nur bei csv_mapping_required öffnet sich die Zuordnung. */
export function needsCsvMapping(format: ImportFormat, _fileName?: string): boolean {
  return format === "csv"
}

/** Antwort csv_mapping_required beim Hochladen → Zuordnung öffnen. */
export const isMappingRequired = (error: unknown): boolean =>
  error instanceof Error && (error as Error & { code?: string }).code === "csv_mapping_required"

/** Nach einem Fehlschlag: Zuordnung öffnen? Nur bei „Automatisch“ ohne bereits offene Zuordnung und Antwort csv_mapping_required. */
export const shouldOpenMapping = (format: ImportFormat, mappingOpen: boolean, error: unknown): boolean =>
  format === "auto" && !mappingOpen && isMappingRequired(error)

/** Alle Texte; no_records bleibt hier der Trade-Import-Text (CRYPTO_MESSAGES) – im Upload-Dialog gilt uploadMessage(). */
export const IMPORT_MESSAGES: Record<string, string> = {
  ...IMPORT_FILE_MESSAGES,
  ...IMPORT_FLOW_MESSAGES,
  ...CRYPTO_MESSAGES,
}

const NO_RECORDS_MT940 = "Im Format „MT940“ wurde keine Buchung gefunden. Echtes MT940 (SWIFT, .sta/.txt) beginnt mit Zeilen wie „:20:“. " + SPARKASSE_CSV_HINT

/** Text zu einem Fehlercode im Bankimport-Upload (no_records je nach gewähltem Format). */
export function uploadMessage(code: string, format?: ImportFormat): string | undefined {
  if (code === "no_records") return format === "mt940" ? NO_RECORDS_MT940 : IMPORT_FILE_MESSAGES.no_records
  return IMPORT_MESSAGES[code]
}

/** Meldung zu einem Fehlercode; unbekannte Codes bleiben lesbar („foo_bar“ → „foo bar“). */
export const importMessage = (code: string): string => IMPORT_MESSAGES[code] ?? code.replaceAll("_", " ")

/** Fehlertext fürs Upload-Formular: bekannte Import-Codes übersetzen, sonst die normale Meldung. */
export function importErrorText(error: unknown, fallback: (error: unknown) => string, uploadFormat?: ImportFormat): string {
  if (error instanceof Error) {
    const { code, params } = error as Error & { code?: string; params?: Record<string, unknown> }
    // Cryptoboard nicht erreichbar: den genauen Grund nennen (nicht installiert / nicht aktiv / Version).
    const reason = typeof params?.reason === "string" ? params.reason : null
    if (code === "crypto_bridge_unavailable" && reason && STALE_REASONS[reason]) {
      return `${STALE_REASONS[reason]} Die Verknüpfung mit Cryptoboard ist deshalb gerade nicht möglich.`
    }
    const lookup = (key: string) => (uploadFormat ? uploadMessage(key, uploadFormat) : IMPORT_MESSAGES[key])
    if (code && lookup(code)) return lookup(code) as string
    if (lookup(error.message)) return lookup(error.message) as string
  }
  return fallback(error)
}

const ENCODING_LABELS: Record<string, string> = { "utf-8": "UTF-8", "utf-8-sig": "UTF-8 mit BOM", cp1252: "Windows-1252", "iso-8859-1": "ISO-8859-1" }
/** „Erkannte Bank: …“ und „Zeichensatz: …“ für die Kopfzeile eines Import-Entwurfs (leer, wenn nichts erkannt wurde). */
export function detectedInfo(batch: { detected_bank?: { label: string } | null; detected_encoding?: string | null }): string[] {
  const parts: string[] = []
  if (batch.detected_bank) parts.push(`Erkannte Bank: ${batch.detected_bank.label}`)
  if (batch.detected_encoding) parts.push(`Zeichensatz: ${ENCODING_LABELS[batch.detected_encoding] ?? batch.detected_encoding}`)
  return parts
}

/** Zeile ist ein vorgemerkter, noch nicht gebuchter Umsatz (Bank-CSV, Info „Umsatz vorgemerkt“). */
export const isPendingRow = (row: { errors: string[] }): boolean => row.errors.includes("pending_transaction")
export const PENDING_LABEL = "Vorgemerkt – noch nicht gebucht"
