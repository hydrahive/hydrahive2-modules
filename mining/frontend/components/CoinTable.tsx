import { useTranslation } from "react-i18next"
import type { CoinRow } from "../api"
import { formatHashrate, formatMoney, formatPercent } from "../format"

export function CoinTable({ rows, hasEur }: { rows: CoinRow[]; hasEur: boolean }) {
  const { t } = useTranslation("mining")
  const best = rows.find((r) => r.usd_day !== null)?.coin
  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <table className="w-full text-sm">
        <thead className="bg-zinc-900/80 text-left text-xs uppercase tracking-wide text-zinc-500">
          <tr>
            <th className="px-3 py-2">{t("col_coin")}</th>
            <th className="px-3 py-2">{t("col_algo")}</th>
            <th className="px-3 py-2 text-right">{t("col_hashrate")}</th>
            <th className="px-3 py-2 text-right">{t("col_fee")}</th>
            <th className="px-3 py-2 text-right">{t("col_day")}</th>
            <th className="px-3 py-2 text-right">{t("col_month")}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {rows.map((r) => {
            const day = hasEur ? r.eur_day : r.usd_day
            const cur = hasEur ? "EUR" : "USD"
            return (
              <tr key={r.coin} className={r.coin === best ? "bg-emerald-500/10" : ""}>
                <td className="px-3 py-2 text-zinc-100">
                  <span className="font-medium">{r.coin.toUpperCase()}</span>
                  <span className="ml-2 text-xs text-zinc-500">{r.name}</span>
                  {r.coin === best && <span className="ml-2 rounded bg-emerald-500/20 px-1.5 text-xs text-emerald-300">{t("best")}</span>}
                </td>
                <td className="px-3 py-2 text-zinc-400">{r.algo}</td>
                <td className="px-3 py-2 text-right text-zinc-300">{formatHashrate(r.hashrate)}</td>
                <td className="px-3 py-2 text-right text-zinc-400" title={r.fee_type === "PROP" ? t("prop_hint") : undefined}>
                  {formatPercent(r.fee)} {r.fee_type}
                </td>
                <td className="px-3 py-2 text-right text-zinc-100" title={r.estimated ? t("estimated_hint") : undefined}>
                  {formatMoney(day, cur)}{r.estimated && day !== null ? " *" : ""}
                </td>
                <td className="px-3 py-2 text-right text-zinc-300">{formatMoney(day === null ? null : day * 30, cur)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
