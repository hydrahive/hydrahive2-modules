import { formatMinorUnits } from "./money"
import { staleReason } from "./cryptoMessages"
import type { CryptoValue } from "./types"
import { Button } from "./ui"
import type { ReportResult } from "./useReport"

export const asOfLabel = (asOf: string): string => {
  const date = new Date(asOf)
  return Number.isNaN(date.getTime()) ? asOf : date.toLocaleString(navigator.language, { dateStyle: "medium", timeStyle: "short" })
}

/** Live-Wert eines verknüpften Wallets neben dem gebuchten Saldo. Fehler bleiben auf der Kontokarte. */
export function CryptoValueView({ state, currency, retry }: { state: ReportResult<CryptoValue> | undefined; currency: string; retry?: () => void }) {
  if (!state) return <p className="mt-2 text-xs text-[#9aa7bc]">Live-Wert wird geladen …</p>
  if (!state.ok) return <div className="mt-2 flex items-center gap-2 text-xs text-[#9aa7bc]"><span>Der Live-Wert konnte gerade nicht geladen werden.</span>{retry && <Button className="px-2 py-1" onClick={retry}>Neu laden</Button>}</div>
  const value = state.data
  if (value.state === "unlinked") return null
  if (value.state === "hidden") return <HiddenNote />
  const money = value.value_minor === null ? null : formatMinorUnits(value.value_minor, currency)
  if (value.state === "stale") return <div className="mt-2 rounded border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-100" role="status">
    <strong>Kurs nicht aktuell</strong>
    <p className="mt-1">{money ? <>Zuletzt bekannter Wert: <strong className="tabular-nums">{money}</strong>{value.as_of ? <> (Stand {asOfLabel(value.as_of)})</> : null}.</> : "Es gibt noch keinen gespeicherten Wert."} {staleReason(value.reason)}</p>
  </div>
  return <div className="mt-2 text-xs text-[#9aa7bc]" role="status">
    <span>Live-Wert (Cryptoboard): </span><strong className="text-sm tabular-nums text-emerald-200">{money ?? "—"}</strong>
    {value.as_of && <span> · Stand {asOfLabel(value.as_of)}</span>}
    {!value.complete && <p className="mt-1 text-amber-200">Unvollständig: Für manche Bestände fehlt ein Kurs, der echte Wert kann höher sein.</p>}
  </div>
}

export function HiddenNote() { return <p className="mt-2 text-xs text-amber-200">Von einem anderen Mitglied verknüpft – der Live-Wert ist nur für dieses Mitglied sichtbar.</p> }
