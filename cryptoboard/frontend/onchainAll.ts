// Reine Logik für „Trades aller Adressen importieren“ (preview_all, Vertrag 1.7.0) — ohne React, ohne Netz.
// Zahlen bleiben Strings (siehe onchainImport.ts). Spam kommt nie in den Commit; Mehrdeutiges nur nach Auswahl;
// Ausgaben (transfer_out) nur, wenn der Nutzer sie anhakt.
import { buildCommitPayload, defaultSelection, isBookable, type Edits } from "./onchainImport"
import type {
  OnchainAllCounts, OnchainCandidate, OnchainCommitResult, OnchainCommitTx, OnchainEntry, OnchainMehrdeutig,
  OnchainPreviewAll,
} from "./types"

/** Auswahl je Mehrdeutig-Gruppe: Schlüssel = tron_tx, Wert = candKey (fehlt/leer = keine Auswahl). */
export type Choice = Record<string, string | undefined>

export const SPAM_GRUENDE = ["symbol_nicht_ascii", "url_im_namen", "unbekannter_token"]

export function candKey(c: Pick<OnchainCandidate, "evm_chain" | "evm_tx">): string {
  return `${c.evm_chain}:${c.evm_tx}`
}

export function chosenCandidate(m: OnchainMehrdeutig, choice: Choice): OnchainCandidate | null {
  const k = choice[m.tron_tx]
  return k ? (m.candidates.find((c) => candKey(c) === k) ?? null) : null
}

/** Einträge der gewählten Mehrdeutig-Kandidaten (die zwei Einträge je Wahl). */
export function chosenEntries(p: Pick<OnchainPreviewAll, "mehrdeutig">, choice: Choice): OnchainEntry[] {
  return p.mehrdeutig.flatMap((m) => chosenCandidate(m, choice)?.entries ?? [])
}

/** Alles, was gebucht werden DARF (wählbar): Tx-Swaps, Paare, gewählte Kandidaten, Ausgaben. Nie Spam. */
export function bookableEntries(p: OnchainPreviewAll, choice: Choice): OnchainEntry[] {
  return [...p.transactions, ...p.pairs.flatMap((x) => x.entries), ...chosenEntries(p, choice), ...p.ausgaben]
}

/** Standard: buchbare Tx-Swaps und Paare angehakt; Ausgaben und Mehrdeutiges NICHT. */
export function defaultSelectionAll(p: OnchainPreviewAll, edits: Edits = {}): Set<string> {
  return defaultSelection([...p.transactions, ...p.pairs.flatMap((x) => x.entries)], edits)
}

/** Kandidat gewählt (key leer = Wahl aufheben): Einträge der alten Wahl raus, buchbare der neuen rein. */
export function applyChoice(selected: Set<string>, m: OnchainMehrdeutig, key: string, edits: Edits): Set<string> {
  const next = new Set(selected)
  for (const c of m.candidates) for (const e of c.entries) next.delete(e.hash)
  const c = m.candidates.find((x) => candKey(x) === key)
  if (c) for (const h of defaultSelection(c.entries, edits)) next.add(h)
  return next
}

/** Ein Kandidat darf nicht in zwei Gruppen gleichzeitig gewählt sein (ein Kauf folgt nur einem Verkauf). */
export function takenElsewhere(p: Pick<OnchainPreviewAll, "mehrdeutig">, choice: Choice, tron_tx: string, key: string) {
  return p.mehrdeutig.some((m) => m.tron_tx !== tron_tx && choice[m.tron_tx] === key)
}

/** Commit-Payload für EINEN Aufruf; nur gewählte + buchbare + erlaubte Einträge. */
export function buildAllPayload(
  p: OnchainPreviewAll, selected: Set<string>, edits: Edits, choice: Choice,
): OnchainCommitTx[] {
  return buildCommitPayload(bookableEntries(p, choice), selected, edits)
}

/** Leer-Zustand laut Vertrag: counts.buchbar == 0 → „Keine Tausch-Transaktionen gefunden“ + Zusammenfassung. */
export function isEmptyResult(c: Pick<OnchainAllCounts, "buchbar">): boolean {
  return c.buchbar === 0
}

export function emptySummary(c: OnchainAllCounts) {
  return { unklar: c.unklar, spam: c.spam, ausgaben: c.ausgaben, mehrdeutig: c.mehrdeutig }
}

/** Verzögerung als Einheit + Zahl („+1 min“): s < 120 → Sekunden, < 2 h → Minuten, sonst Stunden. */
export function formatDelay(seconds: number): { unit: "s" | "min" | "h"; n: number } {
  const s = Math.max(0, Math.round(seconds))
  if (s < 120) return { unit: "s", n: s }
  if (s < 7200) return { unit: "min", n: Math.round(s / 60) }
  return { unit: "h", n: Math.round(s / 3600) }
}

/** Nach dem Commit: Gebuchtes/Duplikate in allen Listen als duplicate markieren (sperrt Doppelbuchung). */
export function markBookedAll(p: OnchainPreviewAll, sent: OnchainCommitTx[], res: OnchainCommitResult) {
  const failed = new Set(res.skipped_details.filter((d) => d.reason !== "duplikat").map((d) => d.hash))
  const booked = new Set(sent.map((t) => t.hash).filter((h) => !failed.has(h)))
  const mark = (e: OnchainEntry): OnchainEntry => (booked.has(e.hash) ? { ...e, duplicate: true } : e)
  const preview: OnchainPreviewAll = {
    ...p,
    transactions: p.transactions.map(mark),
    pairs: p.pairs.map((x) => ({ ...x, entries: x.entries.map(mark) })),
    mehrdeutig: p.mehrdeutig.map((m) => ({
      ...m, candidates: m.candidates.map((c) => ({ ...c, entries: c.entries.map(mark) })),
    })),
    ausgaben: p.ausgaben.map(mark),
  }
  return { preview, booked }
}

/** Kurzform für Fehlerlisten: „0x12345678… sell“ bzw. „tron12345… buy“ — nie das ganze Roh-Format. */
export function hashLabel(hash: string): { tx: string; kind: string } {
  const parts = hash.split(":")
  const tx = parts[0] === "xchain" ? parts[1] : parts[1] ?? hash
  return { tx: `${tx.slice(0, 10)}…`, kind: parts[parts.length - 1] }
}

/** Alle buchbaren, noch nicht gebuchten Einträge einer Liste (für „Alle auswählen“). */
export function selectableHashes(entries: OnchainEntry[], edits: Edits): string[] {
  return entries.filter((e) => !e.duplicate && isBookable(e, edits[e.hash])).map((e) => e.hash)
}

/** Kopfzeile: was liegt zum Buchen bereit (ohne Duplikate). */
export function bookingSummary(p: OnchainPreviewAll) {
  const fresh = p.ausgaben.filter((e) => !e.duplicate)
  return {
    karten: fresh.filter((e) => e.art === "kartenzahlung").length,
    abgaenge: fresh.filter((e) => e.art !== "kartenzahlung").length,
    tausch: [...p.transactions, ...p.pairs.flatMap((x) => x.entries)].filter((e) => !e.duplicate).length,
  }
}
