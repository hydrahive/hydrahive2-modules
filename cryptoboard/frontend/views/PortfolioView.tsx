import { Plus, Wallet } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { rgbFor } from "@/shared/colors"
import { cryptoApi } from "../api"
import { AllocationDonut } from "../components/AllocationDonut"
import { PnlCard } from "../components/PnlCard"
import { TxForm } from "../components/TxForm"
import { fmtPct, fmtPrice, fmtQty, fmtSigned, trendClass } from "../format"
import type { PortfolioSummary } from "../types"

const C = rgbFor("/cryptoboard")
const VS = "eur"

export function PortfolioView() {
  const { t } = useTranslation("cryptoboard")
  const [data, setData] = useState<PortfolioSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData(await cryptoApi.portfolio())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  if (loading && !data) return <p className="p-8 text-center text-sm text-zinc-500">{t("loading")}</p>

  const tot = data?.totals
  const positions = data?.positions ?? []
  const openPositions = positions.filter((p) => p.is_open)

  return (
    <div className="p-5 space-y-4 max-w-6xl mx-auto">
      {/* Summary-Kennzahlen */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
        <PnlCard label={t("pf_total_value")} value={fmtPrice(tot?.value ?? 0, VS)}
          sub={tot ? `${tot.open_count} ${t("pf_positions")}` : null} />
        <PnlCard label={t("pf_unrealized")} value={fmtSigned(tot?.unrealized_pnl ?? 0, VS)}
          sub={fmtPct(tot?.unrealized_pct ?? 0)} trend={tot?.unrealized_pnl ?? 0} />
        <PnlCard label={t("pf_realized")} value={fmtSigned(tot?.realized_pnl ?? 0, VS)}
          trend={tot?.realized_pnl ?? 0} />
        <PnlCard label={t("pf_cost_basis")} value={fmtPrice(tot?.cost_basis ?? 0, VS)} />
      </div>

      {/* Allocation */}
      {openPositions.length > 0 && (
        <CollapsibleBox boxId="cryptoboard-allocation" color={C} icon={<Wallet size={14} />} title={t("pf_allocation")}>
          <div className="box-b py-3">
            <AllocationDonut positions={openPositions} />
          </div>
        </CollapsibleBox>
      )}

      {/* Trade hinzufügen */}
      {adding ? (
        <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-4">
          <h3 className="text-sm font-semibold text-zinc-200 mb-3">{t("tx_add_title")}</h3>
          <TxForm onSaved={() => { setAdding(false); void load() }} onCancel={() => setAdding(false)} />
        </div>
      ) : (
        <button onClick={() => setAdding(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/[4%] text-sm text-zinc-300 hover:bg-white/[7%] transition-colors">
          <Plus size={15} /> {t("tx_add_title")}
        </button>
      )}

      {/* Holdings-Tabelle */}
      <CollapsibleBox boxId="cryptoboard-holdings" color={C} icon={<Wallet size={14} />} title={t("pf_holdings")}>
        <div className="box-b">
          {positions.length === 0 ? (
            <p className="py-6 text-center text-sm text-zinc-500">{t("pf_empty")}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[11px] text-zinc-500 border-b border-white/[6%]">
                    <th className="text-left font-medium py-2 px-2">{t("pf_col_coin")}</th>
                    <th className="text-right font-medium px-2">{t("pf_col_qty")}</th>
                    <th className="text-right font-medium px-2 hidden sm:table-cell">{t("pf_col_avg")}</th>
                    <th className="text-right font-medium px-2">{t("pf_col_price")}</th>
                    <th className="text-right font-medium px-2">{t("pf_col_value")}</th>
                    <th className="text-right font-medium px-2">{t("pf_col_pnl")}</th>
                    <th className="text-right font-medium px-2 hidden md:table-cell">{t("pf_col_alloc")}</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
                    <tr key={p.coin_id} className={`border-b border-white/[3%] hover:bg-white/[2%] ${!p.is_open ? "opacity-50" : ""}`}>
                      <td className="py-2.5 px-2">
                        <Link to={`/cryptoboard/coin/${p.coin_id}`} className="flex items-center gap-2 min-w-0">
                          {p.image && <img src={p.image} alt="" className="w-5 h-5 rounded-full shrink-0" />}
                          <span className="text-zinc-100 truncate">{p.name || p.coin_id}</span>
                          <span className="text-[10px] text-zinc-500 font-mono uppercase shrink-0">{p.symbol}</span>
                        </Link>
                      </td>
                      <td className="text-right tabular-nums px-2 text-zinc-300">{fmtQty(p.quantity)}</td>
                      <td className="text-right tabular-nums px-2 text-zinc-400 hidden sm:table-cell">{fmtPrice(p.avg_cost, VS)}</td>
                      <td className="text-right tabular-nums px-2 text-zinc-300">{fmtPrice(p.price, VS)}</td>
                      <td className="text-right tabular-nums px-2 text-zinc-100">{fmtPrice(p.value, VS)}</td>
                      <td className={`text-right tabular-nums px-2 ${trendClass(p.unrealized_pnl)}`}>
                        {p.is_open ? (
                          <div className="leading-tight">
                            <div>{fmtSigned(p.unrealized_pnl, VS)}</div>
                            <div className="text-[10px]">{fmtPct(p.unrealized_pct)}</div>
                          </div>
                        ) : (
                          <span className="text-zinc-600">{t("pf_closed")}</span>
                        )}
                      </td>
                      <td className="text-right tabular-nums px-2 text-zinc-400 hidden md:table-cell">{p.is_open ? `${p.allocation.toFixed(1)} %` : "—"}</td>
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
