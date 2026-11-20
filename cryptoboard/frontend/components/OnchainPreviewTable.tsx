import { AlertTriangle, Copy, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fmtPrice, fmtQty } from "../format"
import { displayNum, effective, groupPairs, missing, type Edits, type EntryEdit } from "../onchainImport"
import type { OnchainEntry, SearchResult } from "../types"
import { CoinSearch } from "./CoinSearch"

interface Props {
  entries: OnchainEntry[]
  edits: Edits
  selected: Set<string>
  onToggle: (hash: string, on: boolean) => void
  onEdit: (hash: string, edit: EntryEdit) => void
}

const KIND_STYLE: Record<string, string> = { buy: "text-emerald-400", sell: "text-rose-400" }
const input = "w-24 px-1.5 py-0.5 rounded bg-[rgb(var(--hh-s-box,21_28_43)/0.7)] border border-[rgb(var(--hh-s-rand,42_54_75))] text-xs text-right tabular-nums text-[#e8eef8] outline-none"

function Row({ e, edit, checked, onToggle, onEdit }: {
  e: OnchainEntry; edit: EntryEdit | undefined; checked: boolean
  onToggle: Props["onToggle"]; onEdit: Props["onEdit"]
}) {
  const { t } = useTranslation("cryptoboard")
  const eff = effective(e, edit)
  const miss = missing(e, edit)
  const bookable = miss.length === 0
  const pick = (c: SearchResult) => onEdit(e.hash, { ...edit, coin_id: c.id, symbol: c.symbol.toUpperCase(), name: c.name })

  return (
    <tr className={`border-b border-[rgb(var(--hh-s-rand,42_54_75))] align-top ${e.duplicate ? "opacity-50" : ""}`}>
      <td className="py-1.5 px-2">
        <input type="checkbox" checked={checked && bookable} disabled={!bookable}
          onChange={(ev) => onToggle(e.hash, ev.target.checked)} aria-label={t("oc_select")} />
      </td>
      <td className={`px-2 py-1.5 font-medium ${KIND_STYLE[e.kind]}`}>{t(`tx_kind_${e.kind}`)}</td>
      <td className="px-2 py-1.5 text-[#e8eef8]">
        <span className="font-mono uppercase">{eff.symbol}</span>
        {eff.coin_id && <span className="ml-1.5 text-[10px] text-[#9aa7bc]">{eff.name || eff.coin_id}</span>}
        {!e.resolved && !e.duplicate && (
          <div className="mt-1 min-w-48">
            {edit?.coin_id ? (
              <button onClick={() => onEdit(e.hash, { ...edit, coin_id: "", symbol: "", name: "" })}
                className="inline-flex items-center gap-1 text-[10px] text-[#9aa7bc] hover:text-[#c8d2df]">
                <X size={10} /> {t("oc_coin_reset")}
              </button>
            ) : (
              <>
                <span className="flex items-center gap-1 text-[10px] text-amber-400"><AlertTriangle size={11} /> {t("oc_coin_assign")}</span>
                <CoinSearch onPick={pick} placeholder={t("oc_coin_search")} />
              </>
            )}
          </div>
        )}
      </td>
      <td className="px-2 py-1.5 text-right tabular-nums text-[#c8d2df]" title={e.quantity}>{fmtQty(displayNum(e.quantity))}</td>
      <td className="px-2 py-1.5 text-right">
        {e.preis_fehlt && !e.duplicate ? (
          <>
            <input value={edit?.price ?? ""} inputMode="decimal" placeholder="€" aria-label={t("tx_col_price")}
              onChange={(ev) => onEdit(e.hash, { ...edit, price: ev.target.value })}
              className={`${input} ${eff.priceInvalid ? "border-rose-400" : "border-amber-400/70"}`} />
            <div className="text-[10px] text-amber-400">{t("oc_price_required")}</div>
          </>
        ) : (
          <span className="tabular-nums text-[#c8d2df]" title={e.price ?? ""}>{fmtPrice(displayNum(e.price), "eur")}</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-right">
        {e.gebuehr_fehlt && !e.duplicate ? (
          <>
            <input value={edit?.fee ?? ""} inputMode="decimal" placeholder="€" aria-label={t("imp_field_fee")}
              onChange={(ev) => onEdit(e.hash, { ...edit, fee: ev.target.value })}
              className={`${input} ${eff.feeInvalid ? "border-rose-400" : ""}`} />
            <div className="text-[10px] text-[#9aa7bc]">{t("oc_fee_optional")}</div>
          </>
        ) : (
          <span className="tabular-nums text-[#c8d2df]" title={e.fee ?? ""}>{fmtPrice(displayNum(e.fee), "eur")}</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-[10px]">
        {e.duplicate
          ? <span className="inline-flex items-center gap-1 text-[#9aa7bc]"><Copy size={11} /> {t("imp_duplicate")}</span>
          : bookable ? <span className="text-emerald-400">{t("imp_ok")}</span>
          : <span className="text-amber-400">{miss.map((m) => t(`oc_missing_${m}`)).join(", ")}</span>}
      </td>
    </tr>
  )
}

// Vorschau der erkannten Swaps: je Transaktion sell + buy zusammen, Pflichtfelder
// (Preis, Coin) direkt in der Zeile. Duplikate ausgegraut und nicht wählbar.
export function OnchainPreviewTable({ entries, edits, selected, onToggle, onEdit }: Props) {
  const { t } = useTranslation("cryptoboard")
  const pairs = groupPairs(entries)
  return (
    <div className="overflow-x-auto rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))]">
      <table className="w-full text-xs">
        <thead className="bg-[rgb(var(--hh-s-box,21_28_43))]">
          <tr className="text-[10px] uppercase tracking-wider text-[#9aa7bc] border-b border-[rgb(var(--hh-s-rand,42_54_75))]">
            <th className="w-6" />
            <th className="text-left font-medium py-2 px-2">{t("tx_col_kind")}</th>
            <th className="text-left font-medium px-2">{t("imp_col_coin")}</th>
            <th className="text-right font-medium px-2">{t("tx_col_qty")}</th>
            <th className="text-right font-medium px-2">{t("tx_col_price")}</th>
            <th className="text-right font-medium px-2">{t("imp_field_fee")}</th>
            <th className="text-left font-medium px-2">{t("imp_col_status")}</th>
          </tr>
        </thead>
        {pairs.map((p) => (
          <tbody key={p.tx_hash}>
            <tr className="bg-[rgb(var(--hh-s-innen,17_24_39))]">
              <td colSpan={7} className="px-2 py-1 text-[10px] text-[#9aa7bc]">
                <span className="tabular-nums">{p.executed_at ?? "—"}</span>
                <span className="ml-2 font-mono">{p.tx_hash.slice(0, 10)}…{p.tx_hash.slice(-6)}</span>
              </td>
            </tr>
            {p.entries.map((e) => (
              <Row key={e.hash} e={e} edit={edits[e.hash]} checked={selected.has(e.hash)} onToggle={onToggle} onEdit={onEdit} />
            ))}
          </tbody>
        ))}
      </table>
    </div>
  )
}
