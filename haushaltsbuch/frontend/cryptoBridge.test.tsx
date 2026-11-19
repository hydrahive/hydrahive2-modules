// Crypto-Brücke (V9 Phase 3): Kontenzeile live/stale/hidden, Link-Dialog bei „nicht verfügbar“, Trade-Import,
// Transferzeile ohne Kategorie, Meldungen. Ohne Browser-Umgebung (Kern hat kein jsdom): statisches Markup.
import type { ReactNode } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.stubGlobal("navigator", { language: "de-DE" })
vi.mock("@/shared/api-client", () => ({ api: { post: vi.fn(), get: vi.fn() }, buildErrorMessage: () => "Fehler" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/cockpit/admin/ui/AdminDialog", () => ({ AdminDialog: ({ children, footer }: { children: ReactNode; footer: ReactNode }) => <div>{children}{footer}</div> }))
vi.mock("@/features/cockpit/admin/ui/AdminConfirmDialog", () => ({ AdminConfirmDialog: () => null }))
import { api } from "@/shared/api-client"
import { AccountCard } from "./AccountCard"
import { CryptoLinkBody } from "./CryptoLinkDialog"
import { TRADE_IMPORT_HINT, TradeImportResult } from "./CryptoTradeImportDialog"
import { CryptoValueView } from "./CryptoValueView"
import { CRYPTO_MESSAGES } from "./cryptoMessages"
import { fiatAccountOptions, feeCategoryOptions, transferLabel, tradeImportBody } from "./cryptoBridge"
import { haushaltsbuchApi } from "./api"
import { FORMAT_OPTIONS, importErrorText, sourceFormatLabel } from "./importFormats"
import { RowEditor } from "./ImportBatchView"
import type { Account, Category, CryptoBridgeStatus, CryptoValue, Household, ImportBatch, ImportRow } from "./types"

const household = { id: 1, name: "Zuhause", base_currency: "EUR", current_role: "owner" } as Household
const acc = (over: Partial<Account> = {}): Account => ({ id: 5, name: "Mein Wallet", type: "wallet", owner_member_id: null, currency: "EUR", bank_identifier: null, balance_base: 10000, archived: false, revision: 3, linked_portfolio_id: null, linked_by_me: false, crypto_linked: false, ...over })
const value = (over: Partial<CryptoValue>): CryptoValue => ({ account_id: 5, state: "live", value_minor: 123456, as_of: "2026-11-19T10:00:00Z", complete: true, booked_balance: 10000, reason: null, ...over })
const ok = (data: CryptoValue) => ({ ok: true as const, data })
const view = (state: Parameters<typeof CryptoValueView>[0]["state"]) => renderToStaticMarkup(<CryptoValueView state={state} currency="EUR" />)
const card = (account: Account) => renderToStaticMarkup(<AccountCard account={account} household={household} onEdit={() => undefined} onArchive={() => undefined} onLink={() => undefined} onTrades={() => undefined} />)
const codedError = (code: string) => Object.assign(new Error(code), { code, status: 409 })

describe("Live-Wert neben dem gebuchten Saldo", () => {
  it("live: formatierter Wert, kein Roh-Integer, Hinweis bei unvollständig", () => {
    const html = view(ok(value({})))
    expect(html).toContain("1.234,56")
    expect(html).not.toContain("123456")
    expect(html).not.toContain("Kurs nicht aktuell")
    expect(view(ok(value({ complete: false })))).toContain("Unvollständig")
  })
  it("stale: deutlich „Kurs nicht aktuell“, letzter Wert mit Stand, Grund", () => {
    const html = view(ok(value({ state: "stale", reason: "portfolio_unavailable" })))
    expect(html).toContain("Kurs nicht aktuell")
    expect(html).toContain("1.234,56")
    expect(html).toContain("Stand")
    expect(html).toContain("liefert gerade keine Werte")
    const none = view(ok(value({ state: "stale", value_minor: null, as_of: null, reason: "module_not_loaded" })))
    expect(none).toContain("Kurs nicht aktuell")
    expect(none).toContain("noch keinen gespeicherten Wert")
  })
  it("hidden: Hinweis auf anderes Mitglied, kein Wert", () => {
    const html = view(ok(value({ state: "hidden", value_minor: null })))
    expect(html).toContain("Von einem anderen Mitglied verknüpft")
    expect(html).not.toContain("1.234,56")
  })
  it("Fehler des Abrufs bleibt klein und lokal; unlinked zeigt nichts", () => {
    expect(view({ ok: false, error: new Error("x") })).toContain("konnte gerade nicht geladen werden")
    expect(view(ok(value({ state: "unlinked" })))).toBe("")
  })
})

describe("Kontokarte", () => {
  it("Wallet ohne Verknüpfung: Aktion „Mit Cryptoboard verknüpfen“, kein Trade-Import", () => {
    const html = card(acc())
    expect(html).toContain("Mit Cryptoboard verknüpfen")
    expect(html).not.toContain("Trades importieren")
  })
  it("von mir verknüpft: verwalten + Trades; gebuchter Saldo bleibt sichtbar", () => {
    const html = card(acc({ crypto_linked: true, linked_by_me: true, linked_portfolio_id: "p1" }))
    expect(html).toContain("Verknüpfung verwalten")
    expect(html).toContain("Trades importieren")
    expect(html).toContain("gebuchter Saldo")
    expect(html).toContain("100,00")
  })
  it("von anderem Mitglied verknüpft: Hinweis, kein Trade-Import", () => {
    const html = card(acc({ crypto_linked: true, linked_by_me: false }))
    expect(html).toContain("Von einem anderen Mitglied verknüpft")
    expect(html).not.toContain("Trades importieren")
  })
  it("normale Konten haben keine Crypto-Aktionen", () => {
    expect(card(acc({ type: "checking" }))).not.toContain("Cryptoboard")
  })
})

describe("Verknüpfungs-Dialog", () => {
  const body = (status: CryptoBridgeStatus, account = acc()) => renderToStaticMarkup(<CryptoLinkBody account={account} status={status} portfolioId="" onPortfolio={() => undefined} canUnlink busy={false} onReload={() => undefined} />)
  it("bei nicht verfügbar: Hinweis, keine Portfolio-Auswahl", () => {
    const html = body({ available: false, reason: "module_missing", portfolios: [] })
    expect(html).toContain("Cryptoboard ist nicht installiert oder nicht aktiv")
    expect(html).not.toContain("<select")
  })
  it("erklärt Live-Wert, Sperre, Trennen und Sichtbarkeit; bietet nur eigene Portfolios an", () => {
    const html = body({ available: true, reason: null, portfolios: [{ id: "p1", label: "Hauptdepot", currency: "EUR" }] })
    for (const part of ["live aus Cryptoboard", "Manuelle Buchungen sind auf diesem Konto gesperrt", "gebuchten Saldo", "Andere Haushaltsmitglieder sehen den Live-Wert nicht", "Hauptdepot"]) expect(html).toContain(part)
  })
  it("Konflikt (Revision) bekommt die Konflikt-Meldung, fachliche Crypto-Codes nicht", () => {
    const status: CryptoBridgeStatus = { available: true, reason: null, portfolios: [] }
    const conflict = renderToStaticMarkup(<CryptoLinkBody account={acc()} status={status} portfolioId="" onPortfolio={() => undefined} canUnlink busy={false} onReload={() => undefined} error={Object.assign(new Error("x"), { status: 409, code: "revision_conflict" })} />)
    expect(conflict).toContain("Zwischenzeitlich geändert")
    const linked = renderToStaticMarkup(<CryptoLinkBody account={acc()} status={status} portfolioId="" onPortfolio={() => undefined} canUnlink busy={false} onReload={() => undefined} error={codedError("crypto_account_linked")} />)
    expect(linked).not.toContain("Zwischenzeitlich geändert")
    expect(linked).toContain("manuelle Buchungen gesperrt")
  })
})

describe("Trade-Import", () => {
  it("sendet die richtigen Felder (API und Body-Bau)", async () => {
    expect(tradeImportBody(5, "2", "9", "2026-01-01")).toEqual({ wallet_account_id: 5, fiat_account_id: 2, fee_category_id: 9, since: "2026-01-01" })
    expect(tradeImportBody(5, "2", "", "")).toEqual({ wallet_account_id: 5, fiat_account_id: 2, fee_category_id: null, since: null })
    vi.mocked(api.post).mockResolvedValue({ id: 1 })
    await haushaltsbuchApi.createCryptoTradeImport(tradeImportBody(5, "2", "", ""))
    expect(api.post).toHaveBeenCalledWith("/modules/haushaltsbuch/crypto-bridge/trade-imports", { wallet_account_id: 5, fiat_account_id: 2, fee_category_id: null, since: null })
  })
  it("Fiat-Konto: nicht Wallet/archiviert; Gebühren-Kategorie: nur Ausgabe", () => {
    const accounts = [acc({ id: 1, type: "checking" }), acc({ id: 2, type: "wallet" }), acc({ id: 3, type: "savings", archived: true }), acc({ id: 4, type: "cash", currency: "USD" })]
    expect(fiatAccountOptions(accounts, "EUR").map((a) => a.id)).toEqual([1])
    const cats = [{ id: 1, kind: "expense", archived: false }, { id: 2, kind: "income", archived: false }, { id: 3, kind: "expense", archived: true }] as Category[]
    expect(feeCategoryOptions(cats).map((c) => c.id)).toEqual([1])
  })
  it("Hinweis: erst nach Prüfung gebucht; Ergebnis zeigt übersprungene Transfers", () => {
    expect(TRADE_IMPORT_HINT).toContain("erst, nachdem du sie im Prüfbereich kontrolliert")
    const html = renderToStaticMarkup(<TradeImportResult batch={{ id: 1, rows: [{}, {}], warnings: { skipped_transfers: 3 } } as unknown as ImportBatch} />)
    expect(html).toContain("2 Zeile(n)")
    expect(html).toContain("noch nichts gebucht")
    expect(html).toContain("3 Übertrag")
  })
})

describe("Prüfbereich: Umbuchung", () => {
  const row = (over: Partial<ImportRow>): ImportRow => ({ id: 1, batch_id: 1, source_line: 1, booking_date: "2026-11-01", value_date: null, amount_minor: -5000, currency: "EUR", counterparty: "Cryptoboard", purpose: "Kauf 0.1 BTC", counterparty_identifier: null, bank_reference: "r1", category_hint: null, warnings: [], errors: [], fingerprint_strength: "strong", status: "pending", counter_account_id: 5, category_id: null, suggested_category_id: null, suggestion_source: null, suggestion_confidence: null, transaction_id: null, revision: 1, created_at: "", updated_at: "", ...over })
  const accounts = [acc({ id: 5, name: "Mein Wallet" })]
  const render = (r: ImportRow) => renderToStaticMarkup(<RowEditor batchId={1} row={r} accountCurrency="EUR" accounts={accounts} categories={[]} readOnly={false} onUpdated={() => undefined} />)
  it("Kauf (negativ): „Umbuchung auf …“, keine Kategorieauswahl", () => {
    const html = render(row({}))
    expect(html).toContain("Umbuchung auf Mein Wallet")
    expect(html).not.toContain('aria-label="Kategorie"')
    expect(html).toMatch(/[-−]50,00/)
    expect(html).not.toContain("-5000")
  })
  it("Verkauf (positiv): „Umbuchung von …“", () => {
    expect(render(row({ amount_minor: 7000 }))).toContain("Umbuchung von Mein Wallet")
    expect(transferLabel({ counter_account_id: null, amount_minor: 1 }, accounts)).toBeNull()
  })
  it("normale Zeile behält die Kategorieauswahl", () => {
    expect(render(row({ counter_account_id: null }))).toContain('aria-label="Kategorie"')
  })
})

describe("Meldungen und Formate", () => {
  it("crypto_account_linked erklärt die Sperre auf Deutsch, nicht den rohen Code", () => {
    const text = importErrorText(codedError("crypto_account_linked"), () => "roh")
    expect(text).toContain("manuelle Buchungen gesperrt")
    expect(text).not.toContain("crypto_account_linked")
  })
  it("alle crypto_*-Codes aus dem Vertrag haben eine Meldung ohne Unterstrich", () => {
    for (const code of ["crypto_wallet_required", "crypto_portfolio_not_found", "crypto_account_linked", "crypto_currency_unsupported", "crypto_wallet_not_linked", "crypto_link_owner_only", "crypto_fiat_account_invalid", "crypto_fee_category_invalid", "crypto_bridge_unavailable", "crypto_account_not_linked", "crypto_portfolio_already_linked"]) {
      expect(CRYPTO_MESSAGES[code], code).toBeTruthy()
      expect(CRYPTO_MESSAGES[code]).not.toMatch(/crypto_/)
      expect(importErrorText(codedError(code), () => "roh")).toBe(CRYPTO_MESSAGES[code])
    }
  })
  it("crypto_trades: Anzeige „Cryptoboard-Trades“, aber nicht im Upload-Dialog wählbar", () => {
    expect(sourceFormatLabel("crypto_trades")).toBe("Cryptoboard-Trades")
    expect(FORMAT_OPTIONS.map((o) => o.value)).not.toContain("crypto_trades")
  })
})
