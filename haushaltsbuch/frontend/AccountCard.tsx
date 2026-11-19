import { useCallback } from "react"
import { Archive, Link2, Pencil, Repeat, RotateCcw } from "lucide-react"
import { haushaltsbuchApi } from "./api"
import { CryptoValueView, HiddenNote } from "./CryptoValueView"
import { formatMinorUnits } from "./money"
import type { Account, Household } from "./types"
import { Button, panel } from "./ui"
import { useReport } from "./useReport"

/** Lädt den Live-Wert nur für Wallets, die ich selbst verknüpft habe. Ein Fehler bleibt auf dieser Karte. */
function LiveValue({ account, currency }: { account: Account; currency: string }) {
  const load = useCallback(() => haushaltsbuchApi.cryptoValue(account.id), [account.id])
  const { state, retry } = useReport(load)
  return <CryptoValueView state={state} currency={currency} retry={retry} />
}

export interface AccountCardProps {
  account: Account
  household: Household
  onEdit: () => void
  onArchive: () => void
  onLink: () => void
  onTrades: () => void
}

export function AccountCard({ account, household, onEdit, onArchive, onLink, onTrades }: AccountCardProps) {
  const wallet = account.type === "wallet"
  return <article className={`${panel} p-4 ${account.archived ? "opacity-60" : ""}`}>
    <div className="flex items-start gap-2"><div className="min-w-0 flex-1"><h3 className="truncate font-bold text-[#e8eef8]">{account.name}</h3><p className="text-xs text-[#9aa7bc]">{account.type} · {account.currency}{account.archived ? " · Archiviert" : ""}{account.crypto_linked ? " · Cryptoboard" : ""}</p></div><Button className="px-2" aria-label="Bearbeiten" onClick={onEdit}><Pencil size={13} /></Button><Button className="px-2" aria-label={account.archived ? "Reaktivieren" : "Archivieren"} onClick={onArchive}>{account.archived ? <RotateCcw size={13} /> : <Archive size={13} />}</Button></div>
    <p className="mt-4 text-lg font-black tabular-nums text-[#d4deeb]">{formatMinorUnits(account.balance_base, household.base_currency)}</p>
    {account.crypto_linked && <p className="text-xs text-[#9aa7bc]">gebuchter Saldo</p>}
    {account.currency !== household.base_currency && <p className="mt-1 text-xs text-amber-200">Saldo in Basiswährung</p>}
    {wallet && account.linked_by_me && <LiveValue account={account} currency={household.base_currency} />}
    {wallet && account.crypto_linked && !account.linked_by_me && <HiddenNote />}
    {wallet && !account.archived && <div className="mt-3 flex flex-wrap gap-2">
      <Button onClick={onLink}><Link2 size={13} className="mr-1 inline" />{account.crypto_linked ? "Verknüpfung verwalten" : "Mit Cryptoboard verknüpfen"}</Button>
      {account.linked_by_me && <Button onClick={onTrades}><Repeat size={13} className="mr-1 inline" />Trades importieren</Button>}
    </div>}
  </article>
}
