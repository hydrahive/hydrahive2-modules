import { formatMinorUnits } from "./money"
import { ledgerNothingNew } from "./cryptoLedger"
import { ledgerReasonText } from "./cryptoMessages"
import type { LedgerGroup, LedgerGroups } from "./types"
import { panel } from "./ui"

export const LEDGER_HINT = "Erst mit „Buchen“ wird etwas übernommen. Swaps zählen nicht als Ausgabe. Kategorien vergibst du danach selbst („Ohne Kategorie“)."
export const LEDGER_NOTHING_NEW = "Nichts Neues – alle Krypto-Buchungen sind schon übernommen."

function GroupBox({ title, text, group, tone }: { title: string; text: string; group: LedgerGroup; tone: string }) {
  return <div className={`${panel} p-3`} data-testid="ledger-group">
    <h3 className={`text-xs font-bold ${tone}`}>{title}</h3>
    <strong className="mt-1 block text-lg tabular-nums text-[#e8eef8]">{group.count} {group.count === 1 ? "Buchung" : "Buchungen"}</strong>
    <span className="block text-sm tabular-nums text-[#d4deeb]">{formatMinorUnits(group.sum_minor, "EUR")}</span>
    <span className="mt-1 block text-[11px] text-[#9aa7bc]">{text}</span>
  </div>
}

/** Kopf über dem Import-Entwurf des Cryptoboard-Ledgers: Swaps und Kartenzahlungen getrennt, Rest darunter. */
export function CryptoLedgerSummary({ groups }: { groups: LedgerGroups }) {
  const { swaps, kartenzahlungen, abgaenge, unklar, duplicates } = groups
  const nothingNew = ledgerNothingNew(groups)
  return <section className="space-y-3" aria-label="Krypto-Buchungen">
    {nothingNew && <p className="rounded border border-emerald-500/35 bg-emerald-500/10 p-3 text-sm text-emerald-100" role="status">{LEDGER_NOTHING_NEW}</p>}
    <div className="grid gap-3 sm:grid-cols-2">
      <GroupBox title="Umbuchungen (Swaps)" tone="text-cyan-200" group={swaps} text="Tausch zwischen deinen eigenen Krypto-Konten – keine Ausgabe." />
      <GroupBox title="Ausgaben (MetaMask Card)" tone="text-amber-200" group={kartenzahlungen} text="Zahlungen mit USDC – Wert in EUR am Tag, Ausgabe ohne Kategorie." />
    </div>
    <div className={`${panel} space-y-2 p-3 text-xs text-[#d4deeb]`}>
      <p data-testid="ledger-abgaenge"><strong>Sonstige Abgänge (nicht übernommen – du entscheidest):</strong> {abgaenge.count} · {formatMinorUnits(abgaenge.sum_minor, "EUR")}{abgaenge.count > 0 && <span className="text-[#9aa7bc]"> – stehen als „Verworfen“ im Entwurf; wer sie doch buchen will, nimmt sie dort an.</span>}</p>
      <div data-testid="ledger-unklar"><strong>Unklar:</strong> {unklar.length === 0 ? "keine" : unklar.length}
        {unklar.length > 0 && <ul className="mt-1 list-disc space-y-0.5 pl-5 text-amber-100">{unklar.map((item) => <li key={item.id}>{ledgerReasonText(item.reason)} <span className="text-[#9aa7bc]">({item.id})</span></li>)}</ul>}
      </div>
      <p data-testid="ledger-duplicates"><strong>Bereits übernommen:</strong> {duplicates}</p>
    </div>
    <p className="text-xs text-[#9aa7bc]">{LEDGER_HINT}</p>
  </section>
}
