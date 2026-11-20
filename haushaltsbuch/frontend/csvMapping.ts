// CSV-Zuordnung: Startwerte, Spaltenbezeichnungen, Profil-Umwandlung und Prüfung.
import type { CsvColumnMapping, CsvImportMapping, ImportProfile, ImportProfileCreate, ProfileEncoding } from "./types"

/** Standard-Zeichensatz „auto“: das Backend erkennt UTF-8 / Windows-1252 selbst. */
export const EMPTY_MAPPING: CsvImportMapping = {
  booking_date: "", amount: "", debit_amount: "", credit_amount: "", value_date: "",
  currency: "", counterparty: "", purpose: "", bank_reference: "",
  counterparty_identifier: "", category_hint: "", delimiter: ";", encoding: "auto",
  decimal_separator: ",", date_format: "%d.%m.%Y",
}

export const COLUMN_LABELS: { key: keyof CsvColumnMapping; label: string }[] = [
  { key: "booking_date", label: "Buchungsdatum *" }, { key: "amount", label: "Betrag" },
  { key: "debit_amount", label: "Sollbetrag" }, { key: "credit_amount", label: "Habenbetrag" },
  { key: "value_date", label: "Valutadatum" }, { key: "currency", label: "Währung" },
  { key: "counterparty", label: "Gegenpartei" }, { key: "purpose", label: "Verwendungszweck" },
  { key: "bank_reference", label: "Bankreferenz" }, { key: "counterparty_identifier", label: "Gegenkonto" },
  { key: "category_hint", label: "Kategoriehinweis" },
]

/** Profile speichern einen festen Zeichensatz: „auto“ wird durch den erkannten ersetzt. */
export function profileEncoding(encoding: CsvImportMapping["encoding"], detected: string | undefined): ProfileEncoding {
  if (encoding !== "auto") return encoding
  return detected === "cp1252" || detected === "windows-1252" ? "cp1252" : detected === "utf-8-sig" ? "utf-8-sig" : "utf-8"
}

export function profileBody(name: string, mapping: CsvImportMapping, detectedEncoding?: string): ImportProfileCreate {
  const columns: CsvColumnMapping = {
    booking_date: mapping.booking_date,
    amount: mapping.amount || null,
    debit_amount: mapping.debit_amount || null,
    credit_amount: mapping.credit_amount || null,
    value_date: mapping.value_date || null,
    currency: mapping.currency || null,
    counterparty: mapping.counterparty || null,
    purpose: mapping.purpose || null,
    bank_reference: mapping.bank_reference || null,
    counterparty_identifier: mapping.counterparty_identifier || null,
    category_hint: mapping.category_hint || null,
  }
  return { name: name.trim(), delimiter: mapping.delimiter, encoding: profileEncoding(mapping.encoding, detectedEncoding), decimal_separator: mapping.decimal_separator, date_format: mapping.date_format, mapping: columns }
}

export function profileMapping(profile: ImportProfile): CsvImportMapping {
  return { ...EMPTY_MAPPING, ...profile.mapping, delimiter: profile.delimiter, encoding: profile.encoding, decimal_separator: profile.decimal_separator, date_format: profile.date_format }
}

export function validateMapping(mapping: CsvImportMapping): void {
  if (!mapping.booking_date) throw new Error("Ordne die Spalte für das Buchungsdatum zu.")
  const hasAmount = Boolean(mapping.amount)
  const hasPair = Boolean(mapping.debit_amount && mapping.credit_amount)
  if (hasAmount === hasPair) throw new Error("Ordne entweder einen Betrag oder genau ein Soll-/Haben-Spaltenpaar zu.")
}
