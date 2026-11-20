// Ledger-Import (Etappe B4): Fehlertexte und „Nichts Neues“-Prüfung. Geld bleibt Integer-Cent.
import { importErrorText } from "./importFormats"
import type { LedgerGroups } from "./types"

export const LEDGER_ERRORS: Record<string, string> = {
  crypto_bridge_unavailable: "Cryptoboard ist gerade nicht erreichbar oder zu alt für den Ledger-Import. Es wurde nichts angelegt. Bitte versuche es später noch einmal.",
  crypto_wallet_not_linked: "Noch kein Krypto-Konto mit einer Cryptoboard-Adresse verknüpft. Verknüpfe unter „Konten“ zuerst die Adressen deiner Wallets („Adressen verknüpfen“).",
  no_records: "Im Cryptoboard-Ledger gibt es noch keine Buchungen, die sich übernehmen lassen.",
}

/** Klartext zu einem Fehler des Endpunkts; Codes mit Grund (z. B. nicht installiert) behalten ihre genauere Meldung. */
export function ledgerErrorText(error: unknown, fallback: (error: unknown) => string): string {
  const { code, params } = (error instanceof Error ? error : {}) as { code?: string; params?: { reason?: unknown } }
  if (code === "crypto_bridge_unavailable" && typeof params?.reason === "string") return importErrorText(error, fallback)
  const text = (code && LEDGER_ERRORS[code]) || LEDGER_ERRORS[error instanceof Error ? error.message : ""]
  return text ?? importErrorText(error, fallback)
}

/** Alles schon übernommen: nichts Neues, nichts Unklares – nur Duplikate. */
export const ledgerNothingNew = (g: LedgerGroups): boolean =>
  g.swaps.count + g.kartenzahlungen.count + g.abgaenge.count === 0 && g.unklar.length === 0
