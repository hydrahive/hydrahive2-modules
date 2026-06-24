import { TrendingUp } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { rgbFor } from "@/shared/colors"
import { cryptoApi } from "../api"
import { StatCard } from "../components/StatCard"
import { ValueChart } from "../components/ValueChart"
import { fmtPrice, fmtPct, fmtSigned } from "../format"
import type { PortfolioStats, ValueHistory } from "../types"

const C = rgbFor("/cryptoboard")
const VS = "eur"

export function AnalyticsView() {
  const { t } = useTranslation("cryptoboard")
  const [history, setHistory] = useState<ValueHistory | null>(null)
  const [stats, setStats] = useState<PortfolioStats | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      // history lädt fehlende Kurse serverseitig nach (kann beim 1. Mal dauern)
      const [h, s] = await Promise.all([cryptoApi.valueHistory(), cryptoApi.portfolioStats()])
      setHistory(h)
      setStats(s)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  if (loading && !history) {
    return <p className="p-8 text-center text-sm text-zinc-500">{t("an_loading")}</p>
  }

  const empty = !history || history.points.length === 0

  return (
    <div className="p-5 space-y-4 max-w-6xl mx-auto">
      {/* Kennzahlen */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
          <StatCard label={t("an_current")} value={fmtPrice(stats.current, VS)} />
          <StatCard label={t("an_ath")} value={fmtPrice(stats.ath.value, VS)}
            sub={stats.ath.day} />
          <StatCard label={t("an_change_30d")} value={fmtSigned(stats.change_30d.abs, VS)}
            sub={fmtPct(stats.change_30d.pct)} trend={stats.change_30d.abs} />
          <StatCard label={t("an_change_1y")} value={fmtSigned(stats.change_1y.abs, VS)}
            sub={fmtPct(stats.change_1y.pct)} trend={stats.change_1y.abs} />
        </div>
      )}

      {/* Wertverlauf */}
      <CollapsibleBox boxId="cryptoboard-valuechart" color={C} icon={<TrendingUp size={14} />} title={t("an_value_history")}>
        <div className="box-b py-3">
          {empty ? (
            <p className="py-10 text-center text-sm text-zinc-500">{t("an_empty")}</p>
          ) : (
            <>
              <ValueChart points={history!.points} vs={VS} />
              {history!.missing_prices.length > 0 && (
                <p className="mt-2 text-[11px] text-amber-400/80">
                  {t("an_missing")}: {history!.missing_prices.join(", ")}
                </p>
              )}
            </>
          )}
        </div>
      </CollapsibleBox>

      <p className="text-[11px] text-zinc-600 px-1">{t("an_disclaimer")}</p>
    </div>
  )
}
