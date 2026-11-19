import { useState, type FormEvent } from "react"
import { Repeat } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { errorMessage, haushaltsbuchApi, isConflict } from "./api"
import { feeCategoryOptions, fiatAccountOptions, isRevisionConflict, tradeImportBody } from "./cryptoBridge"
import { importErrorText } from "./importFormats"
import type { Account, Category, ImportBatch } from "./types"
import { Button, ErrorState, Field, Input, Select } from "./ui"

export const TRADE_IMPORT_HINT = "Die Trades werden zuerst als Entwurf angelegt. Gebucht wird erst, nachdem du sie im Prüfbereich kontrolliert und den Import abgeschlossen hast. Käufe und Verkäufe erscheinen als Umbuchung zwischen deinem Konto und dem Wallet, Gebühren als Ausgabe. Ein erneuter Import erkennt bereits importierte Trades als Duplikate."

/** Ergebnis nach dem Anlegen: wie viele Zeilen, wie viele Transfers übersprungen wurden, Weg in den Prüfbereich. */
export function TradeImportResult({ batch }: { batch: ImportBatch }) {
  const skipped = batch.warnings?.skipped_transfers ?? 0
  return <div className="grid gap-3 text-sm" role="status">
    <p className="text-emerald-100"><strong>Entwurf angelegt:</strong> {batch.rows?.length ?? 0} Zeile(n) warten auf deine Prüfung. Es wurde noch nichts gebucht.</p>
    {skipped > 0 && <p className="text-amber-100">{skipped} Übertrag/Überträge ({skipped === 1 ? "Ein- oder Auszahlung" : "Ein- und Auszahlungen"} von Coins ohne Euro-Bewegung) wurden übersprungen.</p>}
  </div>
}

export function CryptoTradeImportDialog({ wallet, accounts, categories, baseCurrency, onClose, onOpenBatch }: {
  wallet: Account; accounts: Account[]; categories: Category[]; baseCurrency: string; onClose: () => void; onOpenBatch: (batch: ImportBatch) => void
}) {
  const fiat = fiatAccountOptions(accounts, baseCurrency)
  const fees = feeCategoryOptions(categories)
  const [fiatId, setFiatId] = useState(String(fiat[0]?.id ?? ""))
  const [feeId, setFeeId] = useState("")
  const [since, setSince] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  const [batch, setBatch] = useState<ImportBatch>()
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(undefined)
    if (!fiatId) return setError(new Error("Wähle das Konto, über das gekauft und verkauft wurde."))
    setBusy(true)
    try { setBatch(await haushaltsbuchApi.createCryptoTradeImport(tradeImportBody(wallet.id, fiatId, feeId, since))) }
    catch (cause) { setError(cause) } finally { setBusy(false) }
  }
  return <AdminDialog title="Trades aus Cryptoboard importieren" eyebrow={`Haushaltsbuch · ${wallet.name}`} icon={<Repeat size={16} />} onClose={busy ? undefined : onClose}
    footer={batch ? <><Button onClick={onClose}>Später prüfen</Button><Button tone="primary" onClick={() => onOpenBatch(batch)}>Zur Prüfung</Button></>
      : <><Button onClick={onClose} disabled={busy}>Abbrechen</Button><Button tone="primary" type="submit" form="crypto-trade-form" disabled={busy || !fiat.length}>{busy ? "Wird angelegt …" : "Entwurf anlegen"}</Button></>}>
    {batch ? <TradeImportResult batch={batch} /> : <form id="crypto-trade-form" onSubmit={submit} className="grid gap-4">
      {error !== undefined && <ErrorState error={importErrorText(error, errorMessage)} conflict={isRevisionConflict(error, isConflict)} />}
      <p className="text-xs text-[#9aa7bc]">{TRADE_IMPORT_HINT}</p>
      {!fiat.length && <p className="text-sm text-amber-100">Dafür brauchst du ein aktives Konto in {baseCurrency}, das kein Wallet ist (z. B. ein Girokonto).</p>}
      <Field label="Konto für Käufe und Verkäufe" hint="Von hier geht das Geld beim Kauf weg und kommt beim Verkauf an."><Select required value={fiatId} onChange={(event) => setFiatId(event.target.value)}>{fiat.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.currency})</option>)}</Select></Field>
      <Field label="Kategorie für Gebühren (optional)" hint="Nur Ausgaben-Kategorien. Ohne Kategorie musst du sie im Prüfbereich zuordnen."><Select value={feeId} onChange={(event) => setFeeId(event.target.value)}><option value="">Keine – später zuordnen</option>{fees.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></Field>
      <Field label="Nur Trades ab Datum (optional)"><Input type="date" value={since} onChange={(event) => setSince(event.target.value)} /></Field>
    </form>}
  </AdminDialog>
}
