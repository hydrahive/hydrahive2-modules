import { useState } from "react"
import { Link2 } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { errorMessage, haushaltsbuchApi, isConflict } from "./api"
import { isRevisionConflict } from "./cryptoBridge"
import { importErrorText } from "./importFormats"
import type { Account, CryptoBridgeStatus } from "./types"
import { Button, ErrorState, Field, LoadingState, Select } from "./ui"
import { useReport } from "./useReport"

const EXPLAIN = [
  "Der Wert dieses Kontos kommt live aus Cryptoboard – neben dem gebuchten Saldo.",
  "Manuelle Buchungen sind auf diesem Konto gesperrt; Käufe und Verkäufe holst du über „Trades importieren“.",
  "Beim Trennen fällt das Konto auf den zuletzt gebuchten Saldo zurück. Gebuchtes bleibt unverändert.",
  "Andere Haushaltsmitglieder sehen den Live-Wert nicht, nur dass das Konto verknüpft ist.",
]

interface BodyProps {
  account: Account
  status: CryptoBridgeStatus
  portfolioId: string
  onPortfolio: (id: string) => void
  canUnlink: boolean
  busy: boolean
  error?: unknown
  onReload: () => void
}

/** Inhalt des Dialogs (reine Darstellung – ohne Laden, deshalb ohne Browser testbar). */
export function CryptoLinkBody({ account, status, portfolioId, onPortfolio, canUnlink, busy, error, onReload }: BodyProps) {
  const linkedLabel = status.portfolios.find((p) => p.id === account.linked_portfolio_id)?.label ?? account.linked_portfolio_id
  return <div className="grid gap-4">
    {error !== undefined && <ErrorState error={importErrorText(error, errorMessage)} conflict={isRevisionConflict(error, isConflict)} onRetry={isRevisionConflict(error, isConflict) ? onReload : undefined} />}
    <ul className="list-disc space-y-1 pl-5 text-xs text-[#9aa7bc]">{EXPLAIN.map((line) => <li key={line}>{line}</li>)}</ul>
    {!status.available && !account.crypto_linked && <div className="rounded-[6px] border border-amber-500/35 bg-amber-500/10 p-3 text-sm text-amber-100" role="status">Cryptoboard ist nicht installiert oder nicht aktiv. Verknüpfen ist erst möglich, wenn es läuft.</div>}
    {account.crypto_linked
      ? account.linked_by_me
        ? <p className="text-sm text-[#d4deeb]">Verknüpft mit Portfolio <strong>{linkedLabel}</strong>.</p>
        : <p className="text-sm text-amber-100">Von einem anderen Mitglied verknüpft.{canUnlink ? " Als Haushaltseigentümer kannst du die Verknüpfung trotzdem trennen." : " Nur dieses Mitglied oder der Haushaltseigentümer kann sie trennen."}</p>
      : status.available && (status.portfolios.length
        ? <Field label="Cryptoboard-Portfolio" hint="Es werden nur deine eigenen Portfolios angezeigt."><Select value={portfolioId} disabled={busy} onChange={(event) => onPortfolio(event.target.value)}><option value="">Auswählen …</option>{status.portfolios.map((p) => <option key={p.id} value={p.id}>{p.label} ({p.currency})</option>)}</Select></Field>
        : <p className="text-sm text-[#9aa7bc]">In Cryptoboard gibt es noch kein eigenes Portfolio. Lege dort zuerst eines an.</p>)}
  </div>
}

export function CryptoLinkDialog({ account, isOwner, onClose, onDone }: { account: Account; isOwner: boolean; onClose: () => void; onDone: () => void }) {
  const status = useReport(haushaltsbuchApi.cryptoStatus)
  const [portfolioId, setPortfolioId] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  const canUnlink = account.linked_by_me || isOwner
  async function run(action: () => Promise<unknown>) {
    setBusy(true); setError(undefined)
    try { await action(); onDone() } catch (cause) { setError(cause) } finally { setBusy(false) }
  }
  const link = () => { if (!portfolioId) return setError(new Error("Bitte wähle ein Portfolio aus.")); void run(() => haushaltsbuchApi.linkCrypto(account.id, portfolioId, account.revision)) }
  const unlink = () => { if (window.confirm(`Verknüpfung von „${account.name}“ mit Cryptoboard trennen? Das Konto zeigt danach wieder nur den gebuchten Saldo.`)) void run(() => haushaltsbuchApi.unlinkCrypto(account.id, account.revision)) }
  const result = status.state
  const canLink = !account.crypto_linked && result?.ok === true && result.data.available && result.data.portfolios.length > 0
  return <AdminDialog title={account.crypto_linked ? "Cryptoboard-Verknüpfung" : "Mit Cryptoboard verknüpfen"} eyebrow={`Haushaltsbuch · ${account.name}`} icon={<Link2 size={16} />} onClose={busy ? undefined : onClose}
    footer={<><Button onClick={onClose} disabled={busy}>Schließen</Button>
      {account.crypto_linked && canUnlink && <Button tone="danger" onClick={unlink} disabled={busy}>Verknüpfung trennen</Button>}
      {!account.crypto_linked && <Button tone="primary" onClick={link} disabled={busy || !canLink}>{busy ? "Verknüpft …" : "Verknüpfen"}</Button>}</>}>
    {!result ? <LoadingState label="Cryptoboard wird abgefragt …" />
      : !result.ok ? <ErrorState error={importErrorText(result.error, errorMessage)} onRetry={status.retry} />
      : <CryptoLinkBody account={account} status={result.data} portfolioId={portfolioId} onPortfolio={setPortfolioId} canUnlink={canUnlink} busy={busy} error={error} onReload={onDone} />}
  </AdminDialog>
}
