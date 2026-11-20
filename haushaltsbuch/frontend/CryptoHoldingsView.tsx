import { formatMinorUnits } from "./money"
import { staleReason } from "./cryptoMessages"
import { chainLabel } from "./cryptoBridge"
import { asOfLabel, HiddenNote } from "./CryptoValueView"
import type { CryptoHoldings } from "./types"
import { Button } from "./ui"
import type { ReportResult } from "./useReport"

const cell = "px-2 py-1"

/** Tabelle Coin | Chain | Menge | Wert. Menge bleibt der exakte Decimal-String des Servers (nie gerundet). */
export function HoldingsTable({ data, currency }: { data: CryptoHoldings; currency: string }) {
  const money = (minor: number | null) => (minor === null ? null : formatMinorUnits(minor, currency))
  return <table className="mt-2 w-full text-left text-xs text-[#d4deeb]">
    <thead className="text-[#9aa7bc]"><tr><th className={cell}>Coin</th><th className={cell}>Chain</th><th className={`${cell} text-right`}>Menge</th><th className={`${cell} text-right`}>Wert ({currency})</th></tr></thead>
    <tbody>{data.holdings.map((h) => <tr key={`${h.address_id}-${h.coin_id}`} className="border-t border-[rgb(var(--hh-s-rand,42_54_75))]">
      <td className={`${cell} font-bold`}>{h.symbol}</td><td className={cell}>{chainLabel(h.chain)}</td>
      <td className={`${cell} text-right tabular-nums`}>{h.quantity}</td>
      <td className={`${cell} text-right tabular-nums`}>{money(h.value_minor) ?? <span className="text-amber-200">kein Kurs</span>}</td>
    </tr>)}</tbody>
    <tfoot><tr className="border-t border-[rgb(var(--hh-s-rand-hover,70_97_127))] font-bold"><td className={cell} colSpan={3}>Summe</td><td className={`${cell} text-right tabular-nums text-emerald-200`}>{money(data.value_minor) ?? "—"}</td></tr></tfoot>
  </table>
}

/** Bestand je Coin eines Krypto-Kontos (live oder letzter bekannter Stand). Fehler bleiben auf der Kontokarte. */
export function CryptoHoldingsView({ state, currency, retry }: { state: ReportResult<CryptoHoldings> | undefined; currency: string; retry?: () => void }) {
  if (!state) return <p className="mt-2 text-xs text-[#9aa7bc]">Bestand wird geladen …</p>
  if (!state.ok) return <div className="mt-2 flex items-center gap-2 text-xs text-[#9aa7bc]"><span>Der Bestand konnte gerade nicht geladen werden.</span>{retry && <Button className="px-2 py-1" onClick={retry}>Neu laden</Button>}</div>
  const data = state.data
  if (data.state === "unlinked") return null
  if (data.state === "hidden") return <HiddenNote />
  const stale = data.state === "stale"
  return <div className="mt-2 text-xs text-[#9aa7bc]" role="status">
    {stale && <div className="mb-2 rounded border border-amber-500/40 bg-amber-500/10 p-2 text-amber-100"><strong>Letzter bekannter Stand</strong><p className="mt-1">{staleReason(data.reason)}{data.holdings.length === 0 ? " Es gibt noch keinen gespeicherten Bestand." : ""}</p></div>}
    {data.holdings.length > 0 && <HoldingsTable data={data} currency={currency} />}
    {data.as_of && <p className="mt-1">Stand {asOfLabel(data.as_of)}{stale ? " (nicht aktuell)" : ""}</p>}
    {!data.complete && data.holdings.length > 0 && <p className="mt-1 text-amber-200">Unvollständig – nicht für alle Coins ein Kurs. Der echte Wert kann höher sein.</p>}
  </div>
}
