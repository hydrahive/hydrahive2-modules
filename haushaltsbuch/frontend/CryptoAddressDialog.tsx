import { useState } from "react"
import { Link2 } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { errorMessage, haushaltsbuchApi, isConflict } from "./api"
import { chainLabel, isRevisionConflict, lockedToOtherAccount, selectedAddressIds, shortAddress } from "./cryptoBridge"
import { importErrorText } from "./importFormats"
import type { Account, CryptoBoardAddress } from "./types"
import { Button, ErrorState, LoadingState, panel } from "./ui"
import { useReport } from "./useReport"

interface BodyProps {
  account: Account
  addresses: CryptoBoardAddress[]
  selected: ReadonlySet<number>
  onToggle: (id: number) => void
  busy: boolean
  error?: unknown
  onReload: () => void
}

/** Adressliste mit Checkboxen (reine Darstellung – ohne Laden, deshalb ohne Browser testbar). */
export function CryptoAddressBody({ account, addresses, selected, onToggle, busy, error, onReload }: BodyProps) {
  const conflict = isRevisionConflict(error, isConflict)
  return <div className="grid gap-3">
    {error !== undefined && <ErrorState error={importErrorText(error, errorMessage)} conflict={conflict} onRetry={conflict ? onReload : undefined} />}
    <p className="text-xs text-[#9aa7bc]">Wähle die eigenen Cryptoboard-Adressen, die zu diesem Konto gehören (z. B. Base und Ethereum mit derselben Adresse). Der Bestand wird nur gelesen – es wird nie etwas gesendet oder signiert. Eine Adresse kann nur an einem Konto hängen.</p>
    {addresses.length === 0
      ? <p className="text-sm text-[#9aa7bc]">In Cryptoboard gibt es noch keine eigene Adresse. Lege dort zuerst eine an.</p>
      : <ul className={`${panel} divide-y divide-[rgb(var(--hh-s-rand,38_50_71))]`}>{addresses.map((a) => {
        const locked = lockedToOtherAccount(a, account.id)
        return <li key={a.id} className={locked ? "opacity-60" : ""}><label className="flex items-center gap-3 px-3 py-2 text-sm text-[#d4deeb]">
          <input type="checkbox" checked={selected.has(a.id)} disabled={busy || locked} onChange={() => onToggle(a.id)} aria-label={`${chainLabel(a.chain)} ${shortAddress(a.address)}`} />
          <span className="min-w-0 flex-1"><strong>{chainLabel(a.chain)}</strong> <span className="tabular-nums">{shortAddress(a.address)}</span>{a.label && <span className="ml-2 text-xs text-[#9aa7bc]">{a.label}</span>}
            {locked && <small className="block text-xs text-amber-200">Bereits mit einem anderen Konto verknüpft.</small>}</span>
        </label></li>
      })}</ul>}
  </div>
}

export function CryptoAddressDialog({ account, isOwner, onClose, onDone }: { account: Account; isOwner: boolean; onClose: () => void; onDone: () => void }) {
  const list = useReport(haushaltsbuchApi.cryptoAddresses)
  const [selected, setSelected] = useState<ReadonlySet<number>>(() => new Set(account.crypto_addresses.map((a) => a.address_id)))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  const hasLinks = account.crypto_addresses.length > 0
  const toggle = (id: number) => setSelected((cur) => { const next = new Set(cur); if (next.has(id)) next.delete(id); else next.add(id); return next })
  async function run(action: () => Promise<unknown>) {
    setBusy(true); setError(undefined)
    try { await action(); onDone() } catch (cause) { setError(cause) } finally { setBusy(false) }
  }
  const result = list.state
  const save = () => { if (result?.ok) void run(() => haushaltsbuchApi.linkCryptoAddresses(account.id, selectedAddressIds(result.data, selected), account.revision)) }
  const unlink = () => { if (window.confirm(`Alle Adressen von „${account.name}“ lösen? Das Konto zeigt danach keinen Bestand mehr aus Cryptoboard.`)) void run(() => haushaltsbuchApi.unlinkCryptoAddresses(account.id, account.revision)) }
  return <AdminDialog title="Cryptoboard-Adressen verknüpfen" eyebrow={`Haushaltsbuch · ${account.name}`} icon={<Link2 size={16} />} onClose={busy ? undefined : onClose}
    footer={<><Button onClick={onClose} disabled={busy}>Schließen</Button>
      {hasLinks && (account.linked_by_me || isOwner) && <Button tone="danger" onClick={unlink} disabled={busy}>Alle Adressen lösen</Button>}
      <Button tone="primary" onClick={save} disabled={busy || !result?.ok || selected.size === 0}>{busy ? "Speichert …" : "Speichern"}</Button></>}>
    {!result ? <LoadingState label="Cryptoboard wird abgefragt …" />
      : !result.ok ? <ErrorState error={importErrorText(result.error, errorMessage)} onRetry={list.retry} />
      : <CryptoAddressBody account={account} addresses={result.data} selected={selected} onToggle={toggle} busy={busy} error={error} onReload={onDone} />}
  </AdminDialog>
}
