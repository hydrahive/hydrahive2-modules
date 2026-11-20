// Import-Entwurf: erkannte Bank/Zeichensatz und vorgemerkte Umsätze. Statisches Markup (kein jsdom im Kern).
import type { ReactNode } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.stubGlobal("navigator", { language: "de-DE" })
vi.mock("@/shared/api-client", () => ({ api: { post: vi.fn(), get: vi.fn() }, buildErrorMessage: () => "Fehler" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/cockpit/admin/ui/AdminDialog", () => ({ AdminDialog: ({ children, footer }: { children: ReactNode; footer: ReactNode }) => <div>{children}{footer}</div> }))
vi.mock("@/features/cockpit/admin/ui/AdminConfirmDialog", () => ({ AdminConfirmDialog: () => null }))
import { ImportBatchView, RowEditor } from "./ImportBatchView"
import { detectedInfo } from "./importFormats"
import type { ImportBatch, ImportRow } from "./types"

const row = (over: Partial<ImportRow>): ImportRow => ({
  id: 1, batch_id: 7, source_line: 2, booking_date: "2026-11-02", value_date: null, amount_minor: -1250, currency: "EUR",
  counterparty: "Bäckerei", purpose: "Brötchen", counterparty_identifier: null, bank_reference: null, category_hint: null,
  warnings: [], errors: [], status: "pending", revision: 1, category_id: null, counter_account_id: null,
  suggested_category_id: null, suggestion_source: null, suggestion_confidence: null, fingerprint_strength: "strong", ...over,
} as ImportRow)
const batch = (over: Partial<ImportBatch>): ImportBatch => ({
  id: 7, account_id: 3, profile_id: null, display_filename: "umsaetze.csv", source_format: "csv", status: "draft", revision: 1, rows_revision: 0,
  created_by: "u", created_at: "", updated_at: "", completed_at: null, reversed_at: null, rows: [row({}), row({ id: 2, status: "error", errors: ["pending_transaction"] })], ...over,
})
const view = (b: ImportBatch) => renderToStaticMarkup(<ImportBatchView initialBatch={b} accounts={[]} categories={[]} onBack={() => undefined} onChanged={() => undefined} onDeleted={() => undefined} />)

describe("Import-Entwurf zeigt Erkennung", () => {
  it("erkannte Bank und Zeichensatz stehen in der Kopfzeile", () => {
    const html = view(batch({ detected_bank: { id: "sparkasse_csv_mt940", label: "Sparkasse CSV-MT940" }, detected_encoding: "cp1252" }))
    expect(html).toContain("Erkannte Bank: Sparkasse CSV-MT940")
    expect(html).toContain("Zeichensatz: Windows-1252")
  })
  it("ohne Erkennung (null/fehlend) keine Zusatzangabe", () => {
    expect(detectedInfo({ detected_bank: null, detected_encoding: null })).toEqual([])
    expect(detectedInfo({})).toEqual([])
    expect(view(batch({ detected_bank: null }))).not.toContain("Erkannte Bank")
  })
  it("nur Zeichensatz erkannt (manuelle Zuordnung)", () => {
    expect(detectedInfo({ detected_bank: null, detected_encoding: "utf-8" })).toEqual(["Zeichensatz: UTF-8"])
  })
})

describe("vorgemerkte Umsätze", () => {
  it("Zeile zeigt „Vorgemerkt – noch nicht gebucht“ statt Fehler/Roh-Code", () => {
    const html = renderToStaticMarkup(<RowEditor batchId={7} row={row({ status: "error", errors: ["pending_transaction"] })} accountCurrency="EUR" accounts={[]} categories={[]} readOnly={false} onUpdated={() => undefined} />)
    expect(html).toContain(">Vorgemerkt – noch nicht gebucht</span>") // Statusplakette, nicht „Fehler“
    expect(html).not.toContain(">Fehler</span>")
    expect(html).not.toContain("pending_transaction")
    expect(html).not.toContain("Fehler: ")
    expect(html).not.toContain("pending transaction")
  })
  it("normale Fehlerzeile bleibt „Fehler: …“", () => {
    const html = renderToStaticMarkup(<RowEditor batchId={7} row={row({ status: "error", errors: ["invalid_date"] })} accountCurrency="EUR" accounts={[]} categories={[]} readOnly={false} onUpdated={() => undefined} />)
    expect(html).toContain("Fehler: ")
    expect(html).toContain("Datum")
  })
  it("Fehlerzähler zählt vorgemerkte Zeilen getrennt", () => {
    const html = view(batch({}))
    expect(html).toContain("1 vorgemerkt – noch nicht gebucht")
  })
})
