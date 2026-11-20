// Import PDF/PayPal (V9 Phase 2): Formatwahl, kein CSV-Mapping bei pdf/paypal, verständliche Fehlermeldungen.
// Ohne Browser-Umgebung (Kern hat kein jsdom): statisches Markup, AdminDialog des Kerns als schlichter Rahmen gemockt.
import type { ReactNode } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: {} as Record<string, unknown>, buildErrorMessage: (b: { detail?: { code?: string } }) => b.detail?.code ?? "Fehler" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/cockpit/admin/ui/AdminDialog", () => ({ AdminDialog: ({ children, footer }: { children: ReactNode; footer: ReactNode }) => <div>{children}{footer}</div> }))
import { api } from "@/shared/api-client"
import { errorMessage, haushaltsbuchApi } from "./api"
import { FORMAT_OPTIONS, IMPORT_MESSAGES, importErrorText, importMessage, isMappingRequired, needsCsvMapping, shouldOpenMapping, sourceFormatLabel } from "./importFormats"
import { ImportUploadDialog } from "./ImportUploadDialog"
import { decodeAuto, firstCsvRow } from "./csvHeader"
import { EMPTY_MAPPING, profileEncoding } from "./csvMapping"
import type { ImportFormat } from "./types"

const dialog = (initialFormat?: ImportFormat) => renderToStaticMarkup(
  <ImportUploadDialog accounts={[]} baseCurrency="EUR" profiles={[]} onProfilesChanged={async () => undefined} onClose={() => undefined} onCreated={() => undefined} initialFormat={initialFormat} />)
const codedError = (code: string) => Object.assign(new Error(code), { code, status: 422 })

describe("Import-Dialog", () => {
  it("bietet PDF-Kontoauszug und PayPal-Export an und erlaubt .pdf-Dateien", () => {
    const html = dialog()
    expect(html).toContain("PDF-Kontoauszug")
    expect(html).toContain("PayPal-Export (CSV)")
    expect(html).toContain("MT940 (SWIFT, .sta/.txt)")
    expect(html).toMatch(/accept="[^"]*\.pdf/)
    expect(FORMAT_OPTIONS.map((o) => o.value)).toEqual(["auto", "camt", "mt940", "csv", "pdf", "paypal"])
  })
  it("zeigt bei PDF und PayPal kein CSV-Mapping, aber den Hinweistext", () => {
    const pdf = dialog("pdf")
    expect(pdf).not.toContain("CSV-Zuordnung")
    expect(pdf).toContain("Beleg-Erkennung")
    const paypal = dialog("paypal")
    expect(paypal).not.toContain("CSV-Zuordnung")
    expect(paypal).toContain("Gebühren erscheinen als eigene Zeile")
    expect(dialog("csv")).toContain("CSV-Zuordnung")
  })
  it("Auto-Erkennung behandelt .pdf nicht als CSV", () => {
    expect(needsCsvMapping("auto", "Auszug.PDF")).toBe(false)
    expect(needsCsvMapping("auto", "umsaetze.csv")).toBe(false) // „Automatisch“: direkt hochladen, keine Zuordnung vorab
    expect(needsCsvMapping("pdf", "x.csv")).toBe(false)
    expect(needsCsvMapping("paypal", "x.csv")).toBe(false)
    expect(needsCsvMapping("csv", "x.txt")).toBe(true)
  })
})

describe("Bank-CSV: Automatisch", () => {
  it("Format „Automatisch“ zeigt keine Zuordnung vorab, aber den Sparkasse-Hinweis", () => {
    const html = dialog("auto")
    expect(html).not.toContain("CSV-Zuordnung")
    expect(html.replaceAll("&quot;", "").replaceAll("&#x27;", "")).toContain("CSV-MT940")
    expect(html).toContain("Format „Automatisch“ wählen")
  })
  it("Format „CSV“ zeigt die Zuordnung mit Standard-Zeichensatz „Automatisch“", () => {
    const html = dialog("csv")
    expect(html).toContain("CSV-Zuordnung")
    expect(html).toMatch(/<select[^>]*>\s*<option value="auto" selected[^>]*>Automatisch<\/option>/)
  })
  it("Standard-Zeichensatz der Zuordnung ist „auto“", () => { expect(EMPTY_MAPPING.encoding).toBe("auto") })
  it("Browser-Vorschau „auto“: UTF-8, bei Ersatzzeichen Windows-1252", () => {
    const utf8 = new TextEncoder().encode("Buchungstag;Währung;Betrag\n").buffer as ArrayBuffer
    expect(decodeAuto(utf8).encoding).toBe("utf-8")
    const cp1252 = Uint8Array.from([..."Buchungstag;W".split("").map((c) => c.charCodeAt(0)), 0xE4, ..."hrung;Betrag\n".split("").map((c) => c.charCodeAt(0))]).buffer as ArrayBuffer
    const decoded = decodeAuto(cp1252)
    expect(decoded.encoding).toBe("windows-1252")
    expect(decoded.text).toContain("Währung")
    expect(firstCsvRow(decoded.text, ";")).toEqual(["Buchungstag", "Währung", "Betrag"])
  })
  it("abgeschnittenes UTF-8-Zeichen am Ende des 64-KiB-Kopfs ist kein Zeichensatzfehler", () => {
    const bytes = new TextEncoder().encode("Währung;Betrag\nä")
    expect(decodeAuto(bytes.slice(0, bytes.length - 1).buffer as ArrayBuffer, true).encoding).toBe("utf-8")
  })
  it("csv_mapping_required wird erkannt, andere Fehler nicht", () => {
    expect(isMappingRequired(codedError("csv_mapping_required"))).toBe(true)
    expect(isMappingRequired(codedError("no_records"))).toBe(false)
    expect(isMappingRequired(new Error("x"))).toBe(false)
  })
  it("Zuordnung öffnet sich nur bei „Automatisch“ + csv_mapping_required", () => {
    expect(shouldOpenMapping("auto", false, codedError("csv_mapping_required"))).toBe(true)
    expect(shouldOpenMapping("auto", false, codedError("invalid_date"))).toBe(false)
    expect(shouldOpenMapping("auto", true, codedError("csv_mapping_required"))).toBe(false)
    expect(shouldOpenMapping("csv", false, codedError("csv_mapping_required"))).toBe(false)
    expect(shouldOpenMapping("mt940", false, codedError("csv_mapping_required"))).toBe(false)
  })
  it("csv-preview: POST /imports/csv-preview mit file und account_id", async () => {
    const postForm = vi.fn().mockResolvedValue({ encoding: "cp1252", delimiter: ";", header: ["a"], header_line: 0, bank: null, sample_rows: [] })
    ;(api as unknown as { postForm: typeof postForm }).postForm = postForm
    const file = new File(["x"], "bank.csv")
    await haushaltsbuchApi.csvPreview(file, 3)
    const [path, form] = postForm.mock.calls[0] as [string, FormData]
    expect(path).toBe("/modules/haushaltsbuch/imports/csv-preview")
    expect(form.get("account_id")).toBe("3")
    expect((form.get("file") as File).name).toBe("bank.csv")
  })
  it("Profil mit „Automatisch“ speichert den erkannten festen Zeichensatz", () => {
    expect(profileEncoding("auto", "cp1252")).toBe("cp1252")
    expect(profileEncoding("auto", undefined)).toBe("utf-8")
    expect(profileEncoding("iso-8859-1", "cp1252")).toBe("iso-8859-1")
  })
})

describe("Fehlermeldungen", () => {
  it("pdf_no_text_layer: laienverständlich mit Verweis auf Beleg-Erkennung, nicht der rohe Code", () => {
    const text = importErrorText(codedError("pdf_no_text_layer"), errorMessage)
    expect(text).toContain("keinen lesbaren Text")
    expect(text).toContain("Beleg-Erkennung")
    expect(text).not.toContain("pdf_no_text_layer")
  })
  it("alle Codes des Vertrags haben eine deutsche Meldung (ohne Unterstrich-Codes)", () => {
    for (const code of ["pdf_no_text_layer", "pdf_unreadable", "pdf_too_many_pages", "pdf_no_transactions", "pdf_extraction_unavailable", "paypal_header_invalid", "pdf_line_ambiguous", "paypal_status_not_completed"]) {
      expect(IMPORT_MESSAGES[code], code).toBeTruthy()
      expect(importMessage(code)).not.toContain("_")
      expect(importErrorText(codedError(code), errorMessage)).toBe(IMPORT_MESSAGES[code])
    }
  })
  it("unbekannte Fehler bleiben unverändert", () => {
    expect(importErrorText(new Error("Netz weg"), errorMessage)).toBe("Netz weg")
    expect(importMessage("foo_bar")).toBe("foo bar")
  })
})

describe("Quellformat-Anzeige", () => {
  it("PDF und PayPal haben eigene Beschriftung, die übrigen bleiben wie bisher", () => {
    expect(sourceFormatLabel("pdf")).toBe("PDF")
    expect(sourceFormatLabel("paypal")).toBe("PayPal")
    expect(sourceFormatLabel("camt")).toBe("CAMT")
    expect(sourceFormatLabel("mt940")).toBe("MT940")
  })
})
