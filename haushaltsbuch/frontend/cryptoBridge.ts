// Reine Hilfen der Crypto-Brücke (kein Rechnen mit Geld – Beträge werden nur formatiert angezeigt).
import type { Account, Category, CryptoBoardAddress, CryptoTradeImportBody, ImportRow } from "./types"

/** Manuelle Buchungen sind auf verknüpften Konten gesperrt (Live-Wert aus Cryptoboard). */
export const isCryptoLocked = (account: Pick<Account, "crypto_linked">) => account.crypto_linked

/** Ziel für Trade-Importe: normales, aktives Konto in der Haushaltswährung – kein Wallet. */
export const fiatAccountOptions = (accounts: Account[], baseCurrency: string) =>
  accounts.filter((a) => !a.archived && a.type !== "wallet" && a.currency === baseCurrency)

/** Gebühren-Kategorie: nur Ausgabe, nicht archiviert. */
export const feeCategoryOptions = (categories: Category[]) => categories.filter((c) => c.kind === "expense" && !c.archived)

export function tradeImportBody(walletId: number, fiatId: string, feeCategoryId: string, since: string): CryptoTradeImportBody {
  return { wallet_account_id: walletId, fiat_account_id: Number(fiatId), fee_category_id: feeCategoryId ? Number(feeCategoryId) : null, since: since || null }
}

/** „Umbuchung auf <Konto>“ (Geld geht raus) bzw. „Umbuchung von <Konto>“ (Geld kommt rein) – Richtung aus dem Vorzeichen. */
export function transferLabel(row: Pick<ImportRow, "counter_account_id" | "amount_minor">, accounts: Pick<Account, "id" | "name">[]): string | null {
  if (row.counter_account_id === null) return null
  const name = accounts.find((a) => a.id === row.counter_account_id)?.name ?? `Konto #${row.counter_account_id}`
  return (row.amount_minor ?? 0) < 0 ? `Umbuchung auf ${name}` : `Umbuchung von ${name}`
}

/** Revisionskonflikt (409) – aber nicht die fachlichen 409-Codes der Crypto-Brücke, die eine eigene Meldung haben. */
export function isRevisionConflict(error: unknown, conflict: (e: unknown) => boolean): boolean {
  const code = error instanceof Error ? (error as Error & { code?: string }).code : undefined
  return conflict(error) && !(code ?? "").startsWith("crypto_")
}

const CHAIN_LABELS: Record<string, string> = { base: "Base", ethereum: "Ethereum", tron: "Tron", bitcoin: "Bitcoin" }
export const chainLabel = (chain: string): string => CHAIN_LABELS[chain] ?? (chain ? chain[0].toUpperCase() + chain.slice(1) : chain)

/** Kurzform wie im Backend: „0xa1aE…696E“ (kurze Adressen bleiben ganz). */
export const shortAddress = (address: string): string => (address.length <= 10 ? address : `${address.slice(0, 6)}…${address.slice(-4)}`)

/** Eine Adresse darf nur an einem Konto hängen: an ein ANDERES Konto gebunden → nicht wählbar. */
export const lockedToOtherAccount = (address: Pick<CryptoBoardAddress, "linked_account_id">, accountId: number): boolean =>
  address.linked_account_id !== null && address.linked_account_id !== accountId

/** Gewählte IDs in der Reihenfolge der Adressliste – genau diese gehen an den Server. */
export const selectedAddressIds = (addresses: Pick<CryptoBoardAddress, "id">[], selected: ReadonlySet<number>): number[] =>
  addresses.filter((a) => selected.has(a.id)).map((a) => a.id)
