import { ListPlus, Star } from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { rgbFor } from "@/shared/colors"
import { cryptoApi } from "../api"
import { CoinRow } from "../components/CoinRow"
import { FearGreedGauge } from "../components/FearGreedGauge"
import { PriceCard } from "../components/PriceCard"
import type { MarketRow, WatchItem } from "../types"
import { useVs } from "../vsContext"

const C = rgbFor("/cryptoboard")

export function DashboardView() {
  const { t } = useTranslation("cryptoboard")
  const { vs } = useVs()
  const [watch, setWatch] = useState<WatchItem[]>([])
  const [watchRows, setWatchRows] = useState<MarketRow[]>([])
  const [top, setTop] = useState<MarketRow[]>([])
  const [loading, setLoading] = useState(true)

  const watchedSet = useMemo(() => new Set(watch.map((w) => w.coin_id)), [watch])

  const loadWatch = useCallback(async () => {
    const w = await cryptoApi.watchlist()
    setWatch(w)
    setWatchRows(w.length ? await cryptoApi.markets(w.map((x) => x.coin_id), vs) : [])
  }, [vs])

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([loadWatch(), cryptoApi.top(20, vs)])
      .then(([, topRows]) => { if (alive) setTop(topRows) })
      .catch(() => {})
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [vs, loadWatch])

  const toggle = useCallback(
    async (row: { id: string; symbol: string; name: string }) => {
      if (watchedSet.has(row.id)) await cryptoApi.removeWatch(row.id)
      else await cryptoApi.addWatch(row.id, row.symbol, row.name)
      await loadWatch()
    },
    [watchedSet, loadWatch],
  )

  return (
    <div className="p-5 space-y-4 max-w-6xl mx-auto">
      <div className="rounded-xl border border-white/[6%] bg-white/[2%]">
        <FearGreedGauge />
      </div>

      <CollapsibleBox boxId="cryptoboard-watchlist" color={C} icon={<Star size={14} />} title={t("watchlist")}>
        <div className="box-b">
          {watchRows.length === 0 ? (
            <p className="py-4 text-center text-sm text-zinc-500">{t("watchlist_empty")}</p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
              {watchRows.map((r) => (
                <PriceCard key={r.id} row={r} vs={vs} onRemove={() => toggle(r)} />
              ))}
            </div>
          )}
        </div>
      </CollapsibleBox>

      <CollapsibleBox boxId="cryptoboard-top" color={C} icon={<ListPlus size={14} />} title={t("top_coins")}>
        <div className="box-b">
          <div className="flex items-center gap-3 px-2 pb-1.5 text-[10px] uppercase tracking-wider text-zinc-600 border-b border-white/[5%]">
            <span className="w-6 text-right shrink-0">#</span>
            <span className="flex-1">Coin</span>
            <span className="w-24 text-right shrink-0">{t("col_price")}</span>
            <span className="w-16 text-right shrink-0">{t("col_24h")}</span>
            <span className="hidden md:block w-16 text-right shrink-0">{t("col_7d")}</span>
            <span className="hidden lg:block w-20 shrink-0" />
            <span className="w-6 shrink-0" />
          </div>
          <div className="mt-1 space-y-0.5">
            {top.map((r) => (
              <CoinRow key={r.id} row={r} vs={vs} watched={watchedSet.has(r.id)} onToggle={() => toggle(r)} />
            ))}
          </div>
        </div>
      </CollapsibleBox>

      {loading && <p className="text-center text-xs text-zinc-600">{t("loading")}</p>}
    </div>
  )
}
