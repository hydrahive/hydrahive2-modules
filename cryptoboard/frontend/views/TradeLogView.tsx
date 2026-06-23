import { Pencil, Plus, Trash2, Upload } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { rgbFor } from "@/shared/colors"
import { cryptoApi } from "../api"
import { ImportDialog } from "../components/ImportDialog"
import { TxForm } from "../components/TxForm"
import { fmtPrice, fmtQty } from "../format"
import type { Transaction, TxKind } from "../types"

const C = rgbFor("/cryptoboard")
const VS = "eur"

const KIND_STYLE: Record<TxKind, string> = {
  buy: "text-emerald-400 bg-emerald-500/10",
  sell: "text-rose-400 bg-rose-500/10",
  transfer_in: "text-sky-400 bg-sky-500/10",
  transfer_out: "text-amber-400 bg-amber-500/10",
}

export function TradeLogView() {
  const { t } = useTranslation("cryptoboard")
  const [txs, setTxs] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [importing, setImporting] = useState(false)
  const [editing, setEditing] = useState<Transaction | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      // Neueste zuerst (Store liefert chronologisch aufsteigend → umdrehen)
      const rows = await cryptoApi.transactions()
      setTxs([...rows].reverse())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function del(id: number) {
    if (!window.confirm(t("tx_confirm_delete"))) return
    await cryptoApi.deleteTx(id)
    await load()
  }

  if (loading && txs.length === 0) return <p className="p-8 text-center text-sm text-zinc-500">{t("loading")}</p>

  return (
    <div className="p-5 space-y-4 max-w-5xl mx-auto">
      {(adding || editing) && (
        <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-4">
          <h3 className="text-sm font-semibold text-zinc-200 mb-3">{editing ? t("tx_edit_title") : t("tx_add_title")}</h3>
          <TxForm
            initial={editing}
            onSaved={() => { setAdding(false); setEditing(null); void load() }}
            onCancel={() => { setAdding(false); setEditing(null) }}
          />
        </div>
      )}

      {importing && (
        <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-4">
          <h3 className="text-sm font-semibold text-zinc-200 mb-3">{t("imp_title")}</h3>
          <ImportDialog
            onDone={() => { setImporting(false); void load() }}
            onCancel={() => setImporting(false)}
          />
        </div>
      )}

      {!adding && !editing && !importing && (
        <div className="flex items-center gap-2">
          <button onClick={() => setAdding(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[4%] text-sm text-zinc-300 hover:bg-white/[7%] transition-colors">
            <Plus size={15} /> {t("tx_add_title")}
          </button>
          <button onClick={() => setImporting(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[4%] text-sm text-zinc-300 hover:bg-white/[7%] transition-colors">
            <Upload size={15} /> {t("imp_title")}
          </button>
        </div>
      )}

      <CollapsibleBox boxId="cryptoboard-tradelog" color={C} title={t("nav_tradelog")}>
        <div className="box-b">
          {txs.length === 0 ? (
            <p className="py-6 text-center text-sm text-zinc-500">{t("tx_empty")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[11px] text-zinc-500 border-b border-white/[6%]">
                    <th className="text-left font-medium py-2 px-2">{t("tx_col_date")}</th>
                    <th className="text-left font-medium px-2">{t("tx_col_kind")}</th>
                    <th className="text-left font-medium px-2">{t("tx_col_coin")}</th>
                    <th className="text-right font-medium px-2">{t("tx_col_qty")}</th>
                    <th className="text-right font-medium px-2 hidden sm:table-cell">{t("tx_col_price")}</th>
                    <th className="text-right font-medium px-2 hidden md:table-cell">{t("tx_col_fee")}</th>
                    <th className="px-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {txs.map((tx) => (
                    <tr key={tx.id} className="border-b border-white/[3%] hover:bg-white/[2%] group">
                      <td className="py-2.5 px-2 text-zinc-400 tabular-nums whitespace-nowrap">{tx.executed_at.slice(0, 10)}</td>
                      <td className="px-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${KIND_STYLE[tx.kind]}`}>{t(`tx_kind_${tx.kind}`)}</span>
                      </td>
                      <td className="px-2 text-zinc-200">
                        <span className="font-mono uppercase text-xs">{tx.symbol || tx.coin_id}</span>
                        {tx.note && <span className="ml-2 text-[10px] text-zinc-600">{tx.note}</span>}
                      </td>
                      <td className="text-right tabular-nums px-2 text-zinc-300">{fmtQty(tx.quantity)}</td>
                      <td className="text-right tabular-nums px-2 text-zinc-400 hidden sm:table-cell">{tx.price ? fmtPrice(tx.price, VS) : "—"}</td>
                      <td className="text-right tabular-nums px-2 text-zinc-500 hidden md:table-cell">{tx.fee ? fmtPrice(tx.fee, VS) : "—"}</td>
                      <td className="px-2">
                        <div className="flex items-center gap-1 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => { setEditing(tx); setAdding(false) }} className="p-1 text-zinc-500 hover:text-zinc-200" aria-label="edit"><Pencil size={13} /></button>
                          <button onClick={() => del(tx.id)} className="p-1 text-zinc-500 hover:text-rose-400" aria-label="delete"><Trash2 size={13} /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </CollapsibleBox>
    </div>
  )
}
