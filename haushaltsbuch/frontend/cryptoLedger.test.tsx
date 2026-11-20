// Ledger-Import (Etappe B4): Vorschau-Kopf, Fehlertexte, kein Buchen beim Öffnen. Statisches Markup (kein jsdom im Kern).
import type { ReactNode } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.stubGlobal("navigator", { language: "de-DE" })
vi.mock("@/shared/api-client", () => ({ api: { post: vi.fn(), get: vi.fn() }, buildErrorMessage: () => "Fehler" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/cockpit/admin/ui/AdminDialog", () => ({ AdminDialog: ({ children, footer }: { children: ReactNode; footer: ReactNode }) => <div>{children}{footer}</div> }))
vi.mock("@/features/cockpit/admin/ui/AdminConfirmDialog", () => ({ AdminConfirmDialog: () => null }))
import { api } from "@/shared/api-client"
import { haushaltsbuchApi } from "./api"
import { CryptoLedgerSummary, LEDGER_HINT, LEDGER_NOTHING_NEW } from "./CryptoLedgerSummary"
import { ledgerErrorText, ledgerNothingNew } from "./cryptoLedger"
import { ImportBatchView } from "./ImportBatchView"
import type { ImportBatch, LedgerGroups } from "./types"

const groups = (over: Partial<LedgerGroups> = {}): LedgerGroups => ({
  swaps: { count: 17, sum_minor: 123456 }, kartenzahlungen: { count: 102, sum_minor: 9876543 },
  abgaenge: { count: 3, sum_minor: 4500 }, unklar: [], duplicates: 0, ...over,
})
const summary = (g: LedgerGroups) => renderToStaticMarkup(<CryptoLedgerSummary groups={g} />)
const batch = (g: LedgerGroups): ImportBatch => ({
  id: 9, account_id: 5, profile_id: null, display_filename: "Cryptoboard-Ledger", source_format: "crypto_ledger", status: "draft", revision: 1,
  rows_revision: 0, created_by: "u", created_at: "", updated_at: "", completed_at: null, reversed_at: null, rows: [], groups: g,
})
const coded = (code: string, params?: Record<string, unknown>) => Object.assign(new Error(code), { code, params, status: 422 })
const fallback = () => "Unbekannter Fehler"

describe("Summen aus Cent", () => {
  it("formatiert sum_minor/100 als EUR, kein Roh-Integer", () => {
    const html = summary(groups())
    expect(html).toContain("1.234,56")
    expect(html).toContain("98.765,43")
    expect(html).toContain("45,00")
    expect(html).not.toContain("123456")
    expect(html).not.toContain("9876543")
  })
})

describe("Gruppen getrennt", () => {
  it("Swaps und Kartenzahlungen stehen in eigenen Kästen mit eigener Anzahl", () => {
    const html = summary(groups())
    const boxes = html.split('data-testid="ledger-group"').slice(1)
    expect(boxes).toHaveLength(2)
    expect(boxes[0]).toContain("Umbuchungen (Swaps)"); expect(boxes[0]).toContain("17 Buchungen"); expect(boxes[0]).toContain("1.234,56")
    expect(boxes[0]).not.toContain("98.765,43")
    expect(boxes[1]).toContain("Ausgaben (MetaMask Card)"); expect(boxes[1]).toContain("102 Buchungen"); expect(boxes[1]).toContain("98.765,43")
    expect(boxes[1]).not.toContain("1.234,56")
  })
  it("Abgänge „nicht übernommen – du entscheidest“, Duplikate „bereits übernommen“, Hinweis", () => {
    const html = summary(groups({ duplicates: 4 }))
    expect(html).toContain("Sonstige Abgänge (nicht übernommen – du entscheidest):")
    expect(html).toContain("Bereits übernommen:</strong> 4")
    expect(html).toContain(LEDGER_HINT)
    expect(LEDGER_HINT).toContain("Erst mit „Buchen“ wird etwas übernommen.")
    expect(LEDGER_HINT).toContain("Swaps zählen nicht als Ausgabe.")
    expect(html).not.toContain(LEDGER_NOTHING_NEW)
  })
})

describe("unklar als Klartext", () => {
  it("alle vier Gründe lesbar, kein Roh-Code", () => {
    const html = summary(groups({ unklar: ["kein_eindeutiges_konto", "value_minor_fehlt", "swap_bein_fehlt", "unbekannter_typ"].map((reason, i) => ({ id: `m${i}`, reason })) }))
    expect(html).toContain("Kein eindeutiges Konto")
    expect(html).toContain("Euro-Wert am Tag fehlt")
    expect(html).toContain("Bein")
    expect(html).toContain("Unbekannter Buchungstyp")
    for (const code of ["kein_eindeutiges_konto", "value_minor_fehlt", "swap_bein_fehlt", "unbekannter_typ"]) expect(html).not.toContain(code)
    expect(html).toContain("(m0)")
  })
})

describe("leerer Fall", () => {
  it("alles Duplikat → „Nichts Neues“", () => {
    const empty = groups({ swaps: { count: 0, sum_minor: 0 }, kartenzahlungen: { count: 0, sum_minor: 0 }, abgaenge: { count: 0, sum_minor: 0 }, duplicates: 119 })
    expect(ledgerNothingNew(empty)).toBe(true)
    expect(summary(empty)).toContain("Nichts Neues – alle Krypto-Buchungen sind schon übernommen.")
    expect(summary(empty)).toContain("Bereits übernommen:</strong> 119")
  })
  it("Unklares oder Neues ist nicht „Nichts Neues“", () => {
    expect(ledgerNothingNew(groups())).toBe(false)
    expect(ledgerNothingNew(groups({ swaps: { count: 0, sum_minor: 0 }, kartenzahlungen: { count: 0, sum_minor: 0 }, abgaenge: { count: 0, sum_minor: 0 }, unklar: [{ id: "x", reason: "swap_bein_fehlt" }] }))).toBe(false)
  })
})

describe("Fehler als Klartext", () => {
  it("crypto_bridge_unavailable / crypto_wallet_not_linked / no_records", () => {
    expect(ledgerErrorText(coded("crypto_bridge_unavailable"), fallback)).toContain("Cryptoboard ist gerade nicht erreichbar")
    expect(ledgerErrorText(coded("crypto_wallet_not_linked"), fallback)).toContain("Adressen verknüpfen")
    expect(ledgerErrorText(coded("no_records"), fallback)).toContain("Ledger gibt es noch keine Buchungen")
    for (const code of ["crypto_bridge_unavailable", "crypto_wallet_not_linked", "no_records"]) expect(ledgerErrorText(coded(code), fallback)).not.toContain(code)
  })
  it("Grund bei nicht erreichbar bleibt genauer", () => {
    expect(ledgerErrorText(coded("crypto_bridge_unavailable", { reason: "module_missing" }), fallback)).toContain("nicht installiert")
  })
})

describe("Öffnen bucht nichts", () => {
  beforeEach(() => { vi.mocked(api.post).mockReset() })
  it("Entwurf rendern ruft weder complete noch sonst ein POST", () => {
    const html = renderToStaticMarkup(<ImportBatchView initialBatch={batch(groups())} accounts={[]} categories={[]} onBack={() => undefined} onChanged={() => undefined} onDeleted={() => undefined} />)
    expect(html).toContain("Umbuchungen (Swaps)")
    expect(html).toContain("Import abschließen")
    expect(api.post).not.toHaveBeenCalled()
  })
  it("Endpunkt: nur POST ledger-imports, nie /complete", async () => {
    vi.mocked(api.post).mockResolvedValue(batch(groups()))
    await haushaltsbuchApi.createCryptoLedgerImport()
    expect(api.post).toHaveBeenCalledTimes(1)
    expect(vi.mocked(api.post).mock.calls[0][0]).toBe("/modules/haushaltsbuch/crypto-bridge/ledger-imports")
    expect(vi.mocked(api.post).mock.calls.some(([path]) => String(path).includes("/complete"))).toBe(false)
  })
})
