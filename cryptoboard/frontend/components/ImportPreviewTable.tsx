import { AlertTriangle, Check, Copy } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fmtPrice, fmtQty } from "../format"
import type { ImportTx } from "../types"

interface Props {
  transactions: ImportTx[]
}

const KIND_STYLE: Record<string, string> = {
  buy: "text-emerald-400",
  sell: "text-rose-400",
  transfer_in: "text-sky-400",
  transfer_out: "text-amber-400",
}

// Vorschau-Tabelle der zu importierenden Transaktionen. Markiert Duplikate
// (werden übersprungen) und unauflösbare Symbole (Zeile wird nicht importiert).
export function ImportPreviewTable({ transactions }: Props) {
  const { t } = useTranslation("cryptoboard")
  return (
    <div className="overflow-x-auto max-h-80 overflow-y-auto rounded-lg border border-white/[6%]">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-zinc-900">
          <tr className="text-[10px] uppercase tracking-wider text-zinc-500 border-b border-white/[6%]">
            <th className="text-left font-medium py-2 px-2">{t("tx_col_date")}</th>
            <th className="text-left font-medium px-2">{t("tx_col_kind")}</th>
            <th className="text-left font-medium px-2">{t("imp_col_coin")}</th>
            <th className="text-right font-medium px-2">{t("tx_col_qty")}</th>
            <th className="text-right font-medium px-2">{t("tx_col_price")}</th>
            <th className="text-center font-medium px-2">{t("imp_col_status")}</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx, i) => (
            <tr key={i} className={`border-b border-white/[3%] ${tx.duplicate || !tx.resolved ? "opacity-50" : ""}`}>
              <td className="py-1.5 px-2 text-zinc-400 tabular-nums whitespace-nowrap">{tx.executed_at}</td>
              <td className={`px-2 font-medium ${KIND_STYLE[tx.kind] ?? "text-zinc-400"}`}>{t(`tx_kind_${tx.kind}`)}</td>
              <td className="px-2 text-zinc-200">
                <span className="font-mono uppercase">{tx.symbol}</span>
                {tx.coin_name && <span className="ml-1.5 text-[10px] text-zinc-500">{tx.coin_name}</span>}
              </td>
              <td className="text-right tabular-nums px-2 text-zinc-300">{fmtQty(tx.quantity)}</td>
              <td className="text-right tabular-nums px-2 text-zinc-400">{tx.price ? fmtPrice(tx.price, "eur") : "—"}</td>
              <td className="px-2">
                <div className="flex items-center justify-center">
                  {!tx.resolved ? (
                    <span title={t("imp_unresolved")} className="text-amber-400"><AlertTriangle size={13} /></span>
                  ) : tx.duplicate ? (
                    <span title={t("imp_duplicate")} className="text-zinc-500"><Copy size={13} /></span>
                  ) : (
                    <span title={t("imp_ok")} className="text-emerald-400"><Check size={13} /></span>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
