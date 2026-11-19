// Import PDF/PayPal (V9 Phase 2): Formatwahl, kein CSV-Mapping bei pdf/paypal, verständliche Fehlermeldungen.
// Ohne Browser-Umgebung (Kern hat kein jsdom): statisches Markup, AdminDialog des Kerns als schlichter Rahmen gemockt.
import type { ReactNode } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/shared/api-client", () => ({ api: {}, buildErrorMessage: (b: { detail?: { code?: string } }) => b.detail?.code ?? "Fehler" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/cockpit/admin/ui/AdminDialog", () => ({ AdminDialog: ({ children, footer }: { children: ReactNode; footer: ReactNode }) => <div>{children}{footer}</div> }))
import { errorMessage } from "./api"
import { FORMAT_OPTIONS, IMPORT_MESSAGES, importErrorText, importMessage, needsCsvMapping, sourceFormatLabel } from "./importFormats"
import { ImportUploadDialog } from "./ImportUploadDialog"
import type { ImportFormat } from "./types"

const dialog = (initialFormat?: ImportFormat) => renderToStaticMarkup(
  <ImportUploadDialog accounts={[]} baseCurrency="EUR" profiles={[]} onProfilesChanged={async () => undefined} onClose={() => undefined} onCreated={() => undefined} initialFormat={initialFormat} />)
const codedError = (code: string) => Object.assign(new Error(code), { code, status: 422 })

describe("Import-Dialog", () => {
  it("bietet PDF-Kontoauszug und PayPal-Export an und erlaubt .pdf-Dateien", () => {
    const html = dialog()
    expect(html).toContain("PDF-Kontoauszug")
    expect(html).toContain("PayPal-Export (CSV)")
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
    expect(needsCsvMapping("auto", "umsaetze.csv")).toBe(true)
    expect(needsCsvMapping("pdf", "x.csv")).toBe(false)
    expect(needsCsvMapping("paypal", "x.csv")).toBe(false)
    expect(needsCsvMapping("csv", "x.txt")).toBe(true)
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
