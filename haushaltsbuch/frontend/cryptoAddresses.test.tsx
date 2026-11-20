// Crypto-Brücke v2 (Etappe A1/A2): Adress-Dialog, Bestand je Coin, Kontokarte, Meldungen.
// Ohne Browser-Umgebung (Kern hat kein jsdom): statisches Markup und reine Hilfen.
import type { ReactNode } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.stubGlobal("navigator", { language: "de-DE" })
vi.mock("@/shared/api-client", () => ({ api: { post: vi.fn(), get: vi.fn(), put: vi.fn(), delete: vi.fn() }, buildErrorMessage: () => "Fehler" }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/vault/vaultStore", () => ({ useVaultStore: { getState: () => ({ token: null }) } }))
vi.mock("@/features/cockpit/admin/ui/AdminDialog", () => ({ AdminDialog: ({ children, footer }: { children: ReactNode; footer: ReactNode }) => <div>{children}{footer}</div> }))
vi.mock("@/features/cockpit/admin/ui/AdminConfirmDialog", () => ({ AdminConfirmDialog: () => null }))
import { api } from "@/shared/api-client"
import { AccountCard } from "./AccountCard"
import { CryptoAddressBody } from "./CryptoAddressDialog"
import { CryptoHoldingsView } from "./CryptoHoldingsView"
import { haushaltsbuchApi } from "./api"
import { lockedToOtherAccount, selectedAddressIds } from "./cryptoBridge"
import { CRYPTO_MESSAGES } from "./cryptoMessages"
import { importErrorText } from "./importFormats"
import type { Account, CryptoBoardAddress, CryptoHoldings, Household } from "./types"

const household = { id: 1, name: "Zuhause", base_currency: "EUR", current_role: "owner" } as Household
const acc = (over: Partial<Account> = {}): Account => ({ id: 5, name: "Base/Ethereum", type: "wallet", owner_member_id: null, currency: "EUR", bank_identifier: null, balance_base: 0, archived: false, revision: 7, linked_portfolio_id: null, linked_by_me: false, crypto_linked: false, crypto_addresses: [], ...over })
const addr = (over: Partial<CryptoBoardAddress>): CryptoBoardAddress => ({ id: 2, chain: "base", address: "0xa1aE00000000000000000000000000000000696E", label: null, linked_account_id: null, ...over })
const ADDRESSES = [addr({ id: 2 }), addr({ id: 7, chain: "ethereum" }), addr({ id: 3, chain: "tron", address: "TWgdivAAAAAAAAAAAAAAAAAAAAAAAAZeyD", label: "Tron Haupt", linked_account_id: 9 })]
const body = (account: Account, selected: number[], error?: unknown) => renderToStaticMarkup(<CryptoAddressBody account={account} addresses={ADDRESSES} selected={new Set(selected)} onToggle={() => undefined} busy={false} onReload={() => undefined} error={error} />)

const holdings = (over: Partial<CryptoHoldings> = {}): CryptoHoldings => ({
  account_id: 5, state: "live", value_minor: 123456, as_of: "2026-11-20T10:00:00Z", complete: true, booked_balance: 0, reason: null,
  addresses: [{ id: 2, chain: "base", address: "0xa1aE", label: null }],
  holdings: [
    { chain: "base", address_id: 2, symbol: "ETH", coin_id: "ethereum", quantity: "0.000000000000000001", value_minor: 1, verified: true },
    { chain: "base", address_id: 2, symbol: "USDC", coin_id: "usd-coin", quantity: "1234.56", value_minor: 123455, verified: true },
  ], ...over,
})
const view = (data: CryptoHoldings) => renderToStaticMarkup(<CryptoHoldingsView state={{ ok: true, data }} currency="EUR" />)
const card = (account: Account) => renderToStaticMarkup(<AccountCard account={account} household={household} onEdit={() => undefined} onArchive={() => undefined} onLink={() => undefined} onAddresses={() => undefined} onTrades={() => undefined} />)
const codedError = (code: string, status = 409) => Object.assign(new Error(code), { code, status })

describe("Adress-Dialog", () => {
  it("sendet genau die gewählten address_ids (in Listenreihenfolge) + revision", async () => {
    expect(selectedAddressIds(ADDRESSES, new Set([7, 2]))).toEqual([2, 7])
    expect(selectedAddressIds(ADDRESSES, new Set())).toEqual([])
    vi.mocked(api.put).mockResolvedValue({ id: 5 })
    await haushaltsbuchApi.linkCryptoAddresses(5, selectedAddressIds(ADDRESSES, new Set([7, 2])), 7)
    expect(api.put).toHaveBeenCalledWith("/modules/haushaltsbuch/accounts/5/crypto-addresses", { address_ids: [2, 7], revision: 7 })
  })
  it("Lösen: DELETE mit revision in der Query", async () => {
    vi.mocked(api.delete).mockResolvedValue({ id: 5 })
    await haushaltsbuchApi.unlinkCryptoAddresses(5, 7)
    expect(api.delete).toHaveBeenCalledWith("/modules/haushaltsbuch/accounts/5/crypto-addresses?revision=7")
  })
  it("an ANDEREM Konto gebundene Adresse ist nicht wählbar, die eigene gebundene schon", () => {
    expect(lockedToOtherAccount({ linked_account_id: 9 }, 5)).toBe(true)
    expect(lockedToOtherAccount({ linked_account_id: 5 }, 5)).toBe(false)
    expect(lockedToOtherAccount({ linked_account_id: null }, 5)).toBe(false)
    const html = body(acc(), [2])
    const rows = html.split("<li").filter((li) => li.includes("<input"))
    const tron = rows.find((li) => li.includes("Tron"))!
    expect(tron).toContain("disabled")
    expect(tron).toContain("Bereits mit einem anderen Konto verknüpft")
    const base = rows.find((li) => li.includes("Base"))!
    expect(base).not.toContain("disabled")
    expect(base).toContain("checked")
    expect(html).toContain("0xa1aE…696E")
    expect(html).toContain("TWgdiv…ZeyD")
    expect(html).toContain("Tron Haupt")
  })
  it("Fehlercodes als Klartext, Revisionskonflikt als Konflikt-Meldung", () => {
    for (const code of ["crypto_wallet_required", "crypto_addresses_required", "crypto_bridge_unavailable", "crypto_address_not_found", "crypto_address_already_linked", "crypto_account_not_linked", "owner_only"]) {
      expect(CRYPTO_MESSAGES[code], code).toBeTruthy()
      expect(CRYPTO_MESSAGES[code]).not.toMatch(/crypto_/)
      expect(importErrorText(codedError(code), () => "roh")).toBe(CRYPTO_MESSAGES[code])
      expect(body(acc(), [], codedError(code))).not.toContain(code)
    }
    expect(body(acc(), [], codedError("revision_conflict"))).toContain("Zwischenzeitlich geändert")
    expect(body(acc(), [], codedError("crypto_address_already_linked"))).not.toContain("Zwischenzeitlich geändert")
  })
})

describe("Bestand je Coin", () => {
  it("Menge exakt als String, Wert aus Cent formatiert (kein Rohwert)", () => {
    const html = view(holdings())
    expect(html).toContain("0.000000000000000001")
    expect(html).toContain("1234.56")
    expect(html).toContain("1.234,55")
    expect(html).toContain("1.234,56") // Summe
    expect(html).toContain("0,01")
    expect(html).not.toContain("123456")
    expect(html).not.toContain("1e-18")
    expect(html).toContain("Base")
    expect(html).not.toContain("Unvollständig")
    expect(html).not.toContain("Letzter bekannter Stand")
  })
  it("Wert null → „kein Kurs“; complete=false → Unvollständig-Hinweis", () => {
    const html = view(holdings({ complete: false, value_minor: 5, holdings: [{ chain: "tron", address_id: 3, symbol: "TRX", coin_id: "tron", quantity: "100.5", value_minor: null, verified: true }] }))
    expect(html).toContain("kein Kurs")
    expect(html).toContain("Unvollständig – nicht für alle Coins ein Kurs")
    expect(html).toContain("Tron")
  })
  it("stale: „Letzter bekannter Stand“ + Grund als Klartext, Stand nicht aktuell", () => {
    const html = view(holdings({ state: "stale", reason: "portfolio_unavailable" }))
    expect(html).toContain("Letzter bekannter Stand")
    expect(html).toContain("liefert gerade keine Werte")
    expect(html).not.toContain("portfolio_unavailable")
    expect(html).toContain("0.000000000000000001")
    expect(view(holdings({ state: "stale", reason: "module_not_loaded", holdings: [], value_minor: null, as_of: null }))).toContain("noch keinen gespeicherten Bestand")
  })
  it("hidden → Hinweis ohne Werte; unlinked → nichts; Ladefehler lokal", () => {
    const hidden = view(holdings({ state: "hidden", holdings: [], value_minor: null }))
    expect(hidden).toContain("Von einem anderen Mitglied verknüpft")
    expect(hidden).not.toContain("<table")
    expect(view(holdings({ state: "unlinked", holdings: [] }))).toBe("")
    expect(renderToStaticMarkup(<CryptoHoldingsView state={{ ok: false, error: new Error("x") }} currency="EUR" />)).toContain("konnte gerade nicht geladen werden")
  })
})

describe("Kontokarte mit Adressen", () => {
  const linked = acc({ linked_by_me: true, crypto_addresses: [{ address_id: 2, chain: "base", address_short: "0xa1aE…696E" }, { address_id: 7, chain: "ethereum", address_short: "0xa1aE…696E" }] })
  it("zeigt Adressen kurz, Knopf „Adressen ändern“, Bestand wird geladen", () => {
    const html = card(linked)
    expect(html).toContain("Base 0xa1aE…696E · Ethereum 0xa1aE…696E")
    expect(html).toContain("Adressen ändern")
    expect(html).toContain("Bestand wird geladen")
    expect(html).not.toContain("Live-Wert wird geladen")
  })
  it("ohne Adressen: „Adressen verknüpfen“ und die Portfolio-Verknüpfung bleibt nutzbar", () => {
    const html = card(acc())
    expect(html).toContain("Adressen verknüpfen")
    expect(html).toContain("Mit Cryptoboard verknüpfen")
    expect(html).not.toContain("Bestand wird geladen")
  })
  it("Portfolio-verknüpft ohne Adressen: weiter Portfolio-Wert, nicht Holdings", () => {
    const html = card(acc({ linked_by_me: true, crypto_linked: true, linked_portfolio_id: "p1" }))
    expect(html).toContain("Live-Wert wird geladen")
    expect(html).not.toContain("Bestand wird geladen")
    expect(html).toContain("Trades importieren")
  })
  it("normale Konten haben keine Adress-Aktionen", () => {
    expect(card(acc({ type: "checking" }))).not.toContain("Adressen")
  })
})
