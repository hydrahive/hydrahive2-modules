import { useCallback } from "react"
import { Archive, Link2, Pencil, Repeat, RotateCcw } from "lucide-react"
import { haushaltsbuchApi } from "./api"
import { CryptoHoldingsView } from "./CryptoHoldingsView"
import { CryptoValueView, HiddenNote } from "./CryptoValueView"
import { chainLabel } from "./cryptoBridge"
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

/** Bestand je Coin für Konten mit verknüpften Adressen (nur für den Verknüpfer geladen). */
function Holdings({ account, currency }: { account: Account; currency: string }) {
  const load = useCallback(() => haushaltsbuchApi.cryptoHoldings(account.id), [account.id])
  const { state, retry } = useReport(load)
  return <CryptoHoldingsView state={state} currency={currency} retry={retry} />
}

export interface AccountCardProps {
  account: Account
  household: Household
  onEdit: () => void
  onArchive: () => void
  onLink: () => void
  onAddresses: () => void
  onTrades: () => void
}

export function AccountCard({ account, household, onEdit, onArchive, onLink, onAddresses, onTrades }: AccountCardProps) {
  const wallet = account.type === "wallet"
  const addresses = account.crypto_addresses ?? []
  const hasAddresses = wallet && addresses.length > 0
  return <article className={`${panel} p-4 ${account.archived ? "opacity-60" : ""}`}>
    <div className="flex items-start gap-2"><div className="min-w-0 flex-1"><h3 className="truncate font-bold text-[#e8eef8]">{account.name}</h3><p className="text-xs text-[#9aa7bc]">{account.type} · {account.currency}{account.archived ? " · Archiviert" : ""}{account.crypto_linked ? " · Cryptoboard" : ""}</p></div><Button className="px-2" aria-label="Bearbeiten" onClick={onEdit}><Pencil size={13} /></Button><Button className="px-2" aria-label={account.archived ? "Reaktivieren" : "Archivieren"} onClick={onArchive}>{account.archived ? <RotateCcw size={13} /> : <Archive size={13} />}</Button></div>
    {hasAddresses && <p className="mt-1 text-xs text-[#9aa7bc]">{addresses.map((a) => `${chainLabel(a.chain)} ${a.address_short}`).join(" · ")}</p>}
    <p className="mt-4 text-lg font-black tabular-nums text-[#d4deeb]">{formatMinorUnits(account.balance_base, household.base_currency)}</p>
    {account.crypto_linked && <p className="text-xs text-[#9aa7bc]">gebuchter Saldo</p>}
    {account.currency !== household.base_currency && <p className="mt-1 text-xs text-amber-200">Saldo in Basiswährung</p>}
    {hasAddresses && account.linked_by_me && <Holdings account={account} currency={household.base_currency} />}
    {wallet && !hasAddresses && account.linked_by_me && account.crypto_linked && <LiveValue account={account} currency={household.base_currency} />}
    {wallet && account.crypto_linked && !account.linked_by_me && <HiddenNote />}
    {wallet && !account.archived && <div className="mt-3 flex flex-wrap gap-2">
      <Button onClick={onAddresses}><Link2 size={13} className="mr-1 inline" />{hasAddresses ? "Adressen ändern" : "Adressen verknüpfen"}</Button>
      {(!hasAddresses || account.crypto_linked) && <Button onClick={onLink}><Link2 size={13} className="mr-1 inline" />{account.crypto_linked ? "Verknüpfung verwalten" : "Mit Cryptoboard verknüpfen"}</Button>}
      {account.linked_by_me && account.crypto_linked && <Button onClick={onTrades}><Repeat size={13} className="mr-1 inline" />Trades importieren</Button>}
    </div>}
  </article>
}
