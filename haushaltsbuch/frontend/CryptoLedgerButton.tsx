import { useState } from "react"
import { Coins } from "lucide-react"
import { errorMessage, haushaltsbuchApi } from "./api"
import { ledgerErrorText } from "./cryptoLedger"
import type { ImportBatch } from "./types"
import { Button, ErrorState } from "./ui"

/** Legt den Entwurf aus dem Cryptoboard-Ledger an. Bucht nichts – das passiert erst im Entwurf mit „Import abschließen“. */
export function CryptoLedgerButton({ onCreated }: { onCreated: (batch: ImportBatch) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  async function start() {
    setBusy(true); setError(undefined)
    try { onCreated(await haushaltsbuchApi.createCryptoLedgerImport()) }
    catch (cause) { setError(cause); setBusy(false) }
  }
  return <>
    <Button onClick={start} disabled={busy} title="Legt nur einen Entwurf zur Prüfung an – gebucht wird erst nach deiner Bestätigung."><Coins size={13} className="mr-1 inline" />{busy ? "Wird geprüft …" : "Krypto-Buchungen übernehmen"}</Button>
    {error !== undefined && <div className="w-full"><ErrorState error={ledgerErrorText(error, errorMessage)} /></div>}
  </>
}
