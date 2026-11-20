// Jeder Fehlercode, den das Backend im Bankimport werfen kann, braucht einen deutschen Klartext –
// sonst erscheint er roh („invalid_encoding“). Die Codes werden aus dem Backend-QUELLTEXT gelesen
// (ImportParseError("…"), coded(…, "…"), errors=("…")), damit neue Codes nicht wieder roh erscheinen.
import { readdirSync, readFileSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"
import { IMPORT_MESSAGES, importErrorText, uploadMessage } from "./importFormats"

const BACKEND = join(__dirname, "..", "backend")
const FILES = readdirSync(BACKEND).filter((name) => /^import_.*\.py$/.test(name) || name === "routes_imports.py")
const PATTERNS = [
  /ImportParseError\(\s*"([a-z0-9_]+)"/g,
  /coded\(\s*[^,()]+,\s*"([a-z0-9_]+)"/g,
  /errors=\(\s*"([a-z0-9_]+)"/g,
  /errors\.append\(\s*"([a-z0-9_]+)"/g,
  /warnings\.append\(\s*"([a-z0-9_]+)"/g,
  /errors=\(\*[^,()]+,\s*"([a-z0-9_]+)"/g,
  /_IMMUTABLE_PARSER_ERRORS\s*=\s*\{\s*"([a-z0-9_]+)"/g,
  /warnings=\(\*[^,()]+,\s*"([a-z0-9_]+)"/g,
]
// PDF-Codes entstehen in import_pdf*/Hilfsmodulen mit anderer Schreibweise – hier ausdrücklich mitgeprüft.
const MANUELL = ["pdf_no_text_layer", "pdf_unreadable", "pdf_too_many_pages", "pdf_no_transactions", "pdf_extraction_unavailable"]

function backendCodes(): Map<string, string[]> {
  const found = new Map<string, string[]>()
  for (const name of FILES) {
    const text = readFileSync(join(BACKEND, name), "utf8")
    for (const pattern of PATTERNS) for (const match of text.matchAll(pattern)) found.set(match[1], [...(found.get(match[1]) ?? []), name])
  }
  return found
}

describe("Import-Fehlercodes des Backends", () => {
  const codes = backendCodes()
  it("liest eine plausible Menge Codes aus dem Quelltext (Leseweg intakt)", () => {
    expect(FILES.length).toBeGreaterThan(8)
    expect(codes.size).toBeGreaterThan(30)
    for (const code of ["invalid_encoding", "csv_mapping_required", "pending_transaction", "paypal_currency_conversion_discarded", "no_records", "import_profile_in_use"]) expect(codes.has(code), code).toBe(true)
  })
  it("jeder Code hat einen deutschen Klartext", () => {
    const ohneText = [...codes.keys()].filter((code) => !IMPORT_MESSAGES[code])
    expect(ohneText, `Codes ohne Text in importMessages.ts: ${ohneText.join(", ")}`).toEqual([])
  })
  it("Texte sind Sätze (mind. 25 Zeichen, kein Roh-Code, nicht nur der Code selbst)", () => {
    for (const code of codes.keys()) {
      const text = IMPORT_MESSAGES[code] ?? ""
      expect(text.length, code).toBeGreaterThanOrEqual(25)
      expect(text, code).not.toContain(code)
      expect(text, code).not.toMatch(/[a-z]+_[a-z]+/)
    }
  })
  it("die geforderte Codeliste ist vollständig abgedeckt", () => {
    for (const code of [...MANUELL, "camt_batch_amount_missing", "csv_column_missing", "csv_header_missing", "csv_mapping_required", "debit_credit_invalid", "file_too_large", "invalid_amount", "invalid_camt_contract", "invalid_camt_record", "invalid_currency", "invalid_date", "invalid_encoding", "invalid_mt940_record", "invalid_xml", "invalid_xml_encoding", "no_records", "paypal_header_invalid", "too_many_records", "unsupported_camt_version", "unsupported_format", "xml_declaration_forbidden", "account_archived", "duplicate_import_file", "duplicate_import_row", "import_category_kind_mismatch", "import_category_required", "import_profile_conflict", "import_profile_in_use", "import_row_has_errors", "import_row_incomplete", "invalid_csv_mapping", "no_accepted_import_rows", "pending_transaction", "paypal_currency_conversion_discarded"]) expect(IMPORT_MESSAGES[code], code).toBeTruthy()
  })
  it("Server-Fehler mit Code erscheint im Dialog als Klartext, nicht roh", () => {
    const err = Object.assign(new Error("invalid_encoding"), { code: "invalid_encoding", status: 422 })
    const text = importErrorText(err, (e) => (e as Error).message)
    expect(text).not.toBe("invalid_encoding")
    expect(text).toContain("Zeichen")
  })
  it("no_records bei MT940 nennt den Sparkasse-Hinweis, bei anderen Formaten den allgemeinen Text", () => {
    const err = Object.assign(new Error("no_records"), { code: "no_records", status: 422 })
    const mt940 = importErrorText(err, () => "roh", "mt940")
    expect(mt940).toContain("CSV-MT940")
    expect(mt940).toContain("Automatisch")
    expect(uploadMessage("no_records", "auto")).toContain("keine Buchung")
    expect(uploadMessage("no_records", "auto")).toContain("CSV-MT940")
  })
})
