// Reine Logik des On-Chain-Trade-Imports (ohne React, ohne Netz) — testbar ohne jsdom.
// Zahlen bleiben Strings: Mengen/Preise/Gebühren werden NIE über Number() gerundet,
// sondern exakt so an den Commit gereicht, wie Backend oder Nutzer sie liefern.
import type { OnchainCommitResult, OnchainCommitTx, OnchainCounts, OnchainEntry, OnchainPreview } from "./types"

/** Nutzer-Ergänzungen je Eintrag (Schlüssel: entry.hash). */
export interface EntryEdit {
  coin_id?: string
  symbol?: string
  name?: string
  price?: string
  fee?: string
}
export type Edits = Record<string, EntryEdit>

export interface TxPair {
  tx_hash: string
  executed_at: string | null
  entries: OnchainEntry[] // sell zuerst, dann buy
}

const DEC_RE = /^\d+(\.\d+)?$/

/** Eingabe → Dezimal-String ("1,5" → "1.5"); ungültig → null. Rein textuell, keine Rundung. */
export function normDecimal(input: string | null | undefined): string | null {
  if (input == null) return null
  const s = input.trim().replace(",", ".")
  return DEC_RE.test(s) ? s : null
}

/** sell/buy-Einträge je tx_hash zusammenfassen, Reihenfolge der ersten Sichtung. */
export function groupPairs(entries: OnchainEntry[]): TxPair[] {
  const map = new Map<string, TxPair>()
  for (const e of entries) {
    let p = map.get(e.tx_hash)
    if (!p) {
      p = { tx_hash: e.tx_hash, executed_at: e.executed_at, entries: [] }
      map.set(e.tx_hash, p)
    }
    p.entries.push(e)
  }
  for (const p of map.values()) p.entries.sort((a, b) => (a.kind === b.kind ? 0 : a.kind === "sell" ? -1 : 1))
  return [...map.values()]
}

/** Eintrag mit Nutzer-Ergänzungen. Leere Ergänzung = Backend-Wert. */
export function effective(e: OnchainEntry, edit: EntryEdit | undefined) {
  const coin_id = edit?.coin_id || e.coin_id
  const priceRaw = edit?.price !== undefined && edit.price.trim() !== "" ? edit.price : e.price
  const feeRaw = edit?.fee !== undefined && edit.fee.trim() !== "" ? edit.fee : e.fee
  return {
    coin_id: coin_id || null,
    symbol: edit?.symbol || e.symbol,
    name: edit?.name || e.name,
    price: priceRaw == null ? null : normDecimal(priceRaw),
    priceInvalid: priceRaw != null && normDecimal(priceRaw) == null,
    fee: feeRaw == null ? null : normDecimal(feeRaw),
    feeInvalid: feeRaw != null && normDecimal(feeRaw) == null,
  }
}

export type Missing = "duplicate" | "coin" | "price" | "fee_invalid" | "time"

/** Warum ist ein Eintrag (noch) nicht buchbar? Leere Liste = buchbar. */
export function missing(e: OnchainEntry, edit: EntryEdit | undefined): Missing[] {
  if (e.duplicate) return ["duplicate"]
  const eff = effective(e, edit)
  const out: Missing[] = []
  if (!eff.coin_id) out.push("coin")
  // transfer_out: Preis nur zur Information, ohne Preis buchbar (Backend bucht 0).
  if (eff.price == null && e.kind !== "transfer_out") out.push("price")
  if (eff.feeInvalid) out.push("fee_invalid")
  if (!e.executed_at) out.push("time")
  return out
}

export function isBookable(e: OnchainEntry, edit: EntryEdit | undefined): boolean {
  return missing(e, edit).length === 0
}

/** Standardauswahl: alle beim Laden buchbaren Einträge. */
export function defaultSelection(entries: OnchainEntry[], edits: Edits = {}): Set<string> {
  return new Set(entries.filter((e) => isBookable(e, edits[e.hash])).map((e) => e.hash))
}

/** Commit-Payload: nur gewählte UND buchbare Einträge, Zahlen als unveränderte Strings. */
export function buildCommitPayload(entries: OnchainEntry[], selected: Set<string>, edits: Edits): OnchainCommitTx[] {
  const out: OnchainCommitTx[] = []
  for (const e of entries) {
    if (!selected.has(e.hash)) continue
    const edit = edits[e.hash]
    if (!isBookable(e, edit)) continue
    const eff = effective(e, edit)
    out.push({
      coin_id: eff.coin_id as string,
      symbol: eff.symbol,
      name: eff.name,
      kind: e.kind,
      quantity: e.quantity,
      price: eff.price,
      fee: eff.fee,
      executed_at: e.executed_at as string,
      hash: e.hash,
    })
  }
  return out
}

function byHash<T extends { hash: string }>(a: T[], b: T[]): T[] {
  const seen = new Set(a.map((x) => x.hash))
  return [...a, ...b.filter((x) => !seen.has(x.hash) && seen.add(x.hash))]
}

export function countsOf(p: Pick<OnchainPreview, "transactions" | "wraps" | "unklar">): OnchainCounts {
  const tx = p.transactions
  return {
    swaps: new Set(tx.map((e) => e.tx_hash)).size,
    transactions: tx.length,
    wraps: p.wraps.length,
    unklar: p.unklar.length,
    duplicates: tx.filter((e) => e.duplicate).length,
    preis_fehlt: tx.filter((e) => e.preis_fehlt).length,
    gebuehr_fehlt: tx.filter((e) => e.gebuehr_fehlt).length,
    unresolved: tx.filter((e) => !e.resolved).length,
  }
}

/** „Ältere nachladen“: neue Seite anhängen, je Liste nach hash dedupliziert. */
export function mergePreview(prev: OnchainPreview, next: OnchainPreview): OnchainPreview {
  const merged = {
    ...next,
    transactions: byHash(prev.transactions, next.transactions),
    wraps: byHash(prev.wraps, next.wraps),
    unklar: byHash(prev.unklar, next.unklar),
    kurs_abruf_fehlgeschlagen: prev.kurs_abruf_fehlgeschlagen || next.kurs_abruf_fehlgeschlagen,
  }
  return { ...merged, counts: countsOf(merged) }
}

/** Nach dem Commit: gebuchte und als Duplikat übersprungene Einträge als duplicate markieren. */
export function markBooked(p: OnchainPreview, sent: OnchainCommitTx[], res: OnchainCommitResult) {
  const failed = new Set(res.skipped_details.filter((d) => d.reason !== "duplikat").map((d) => d.hash))
  const booked = new Set(sent.map((t) => t.hash).filter((h) => !failed.has(h)))
  const transactions = p.transactions.map((e) => (booked.has(e.hash) ? { ...e, duplicate: true } : e))
  const merged = { ...p, transactions }
  return { preview: { ...merged, counts: countsOf(merged) }, booked }
}

/** Fehlercodes, für die es einen eigenen Klartext gibt (sonst Backend-Meldung). */
export const KNOWN_ERRORS = [
  "address_not_found", "onchain_chain_not_supported", "alchemy_key_missing", "alchemy_key_invalid",
  "alchemy_base_not_enabled", "alchemy_network_error", "alchemy_fetch_failed", "alchemy_test_failed",
  "alchemy_key_empty", "cryptoboard_onchain_disabled", "tron_network_error", "tron_fetch_failed",
] as const

export function errorKey(err: unknown): string | null {
  const code = (err as { code?: unknown } | null)?.code
  return typeof code === "string" && (KNOWN_ERRORS as readonly string[]).includes(code) ? `oc_err_${code}` : null
}

export const SKIP_REASONS = ["duplikat", "preis_fehlt", "coin_id_fehlt", "hash_ungueltig", "zeit_ungueltig", "ledger_full", "ungueltig"]
export const UNKLAR_REASONS = [
  "keine_nettobewegung", "mehrdeutige_bewegung", "decimals_fehlt", "nur_raus", "nur_rein", "mehrere_assets",
]

/** Nur für die Anzeige (Formatierer erwarten Zahlen) — nie für Payloads verwenden. */
export function displayNum(s: string | null | undefined): number | null {
  if (s == null) return null
  const n = Number(s)
  return Number.isFinite(n) ? n : null
}
