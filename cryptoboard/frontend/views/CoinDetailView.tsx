import { ArrowLeft, Check, Plus } from "lucide-react"
import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { cryptoApi } from "../api"
import { PriceChart } from "../components/PriceChart"
import { fmtCompact, fmtPct, fmtPrice, fmtSupply, trendClass } from "../format"
import type { CoinDetail, WatchItem } from "../types"
import { useVs } from "../vsContext"

const TIMEFRAMES = [
  { key: "tf_24h", days: "1" },
  { key: "tf_7d", days: "7" },
  { key: "tf_30d", days: "30" },
  { key: "tf_1y", days: "365" },
]

export function CoinDetailView() {
  const { t } = useTranslation("cryptoboard")
  const { vs } = useVs()
  const { id = "" } = useParams()
  const [coin, setCoin] = useState<CoinDetail | null>(null)
  const [prices, setPrices] = useState<[number, number][]>([])
  const [days, setDays] = useState("7")
  const [watched, setWatched] = useState(false)
  const [err, setErr] = useState(false)

  useEffect(() => {
    setErr(false)
    setCoin(null)
    cryptoApi.coin(id, vs).then(setCoin).catch(() => setErr(true))
    cryptoApi.watchlist().then((w: WatchItem[]) => setWatched(w.some((x) => x.coin_id === id))).catch(() => {})
  }, [id, vs])

  useEffect(() => {
    cryptoApi.chart(id, days, vs).then((r) => setPrices(r.prices)).catch(() => setPrices([]))
  }, [id, days, vs])

  async function toggleWatch() {
    if (!coin) return
    if (watched) {
      await cryptoApi.removeWatch(id)
      setWatched(false)
    } else {
      await cryptoApi.addWatch(id, coin.symbol, coin.name)
      setWatched(true)
    }
  }

  if (err) return <div className="p-5 text-sm text-rose-400">{t("error")}</div>
  if (!coin) return <div className="p-5 text-sm text-zinc-500">{t("loading")}</div>

  const stats = [
    { label: t("rank"), value: coin.market_cap_rank ? `#${coin.market_cap_rank}` : "—" },
    { label: t("col_cap"), value: fmtCompact(coin.market_cap, vs) },
    { label: t("col_vol"), value: fmtCompact(coin.volume, vs) },
    { label: t("ath"), value: fmtPrice(coin.ath, vs) },
    { label: t("atl"), value: fmtPrice(coin.atl, vs) },
    { label: t("circulating"), value: fmtSupply(coin.circulating_supply) },
    { label: t("total_supply"), value: fmtSupply(coin.total_supply) },
    { label: t("max_supply"), value: fmtSupply(coin.max_supply) },
  ]

  return (
    <div className="p-5 max-w-5xl mx-auto space-y-4">
      <Link to="/cryptoboard" className="inline-flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors">
        <ArrowLeft size={13} />
        {t("back")}
      </Link>

      <div className="flex items-center gap-3 flex-wrap">
        {coin.image && <img src={coin.image} alt="" className="w-10 h-10 rounded-full" />}
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white">{coin.name}</h2>
            <span className="text-sm text-zinc-500 font-mono uppercase">{coin.symbol}</span>
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-2xl font-semibold text-zinc-50 tabular-nums">{fmtPrice(coin.price, vs)}</span>
            <span className={`text-sm font-mono tabular-nums ${trendClass(coin.change_24h)}`}>{fmtPct(coin.change_24h)} (24h)</span>
          </div>
        </div>
        <button
          onClick={toggleWatch}
          className={`ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${watched ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-white/10 text-zinc-300 hover:bg-white/5"}`}
        >
          {watched ? <Check size={14} /> : <Plus size={14} />}
          {watched ? t("remove_watch") : t("add_watch")}
        </button>
      </div>

      <div className="rounded-xl border border-white/[6%] bg-white/[2%] p-3">
        <div className="flex justify-end gap-1 mb-2">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.days}
              onClick={() => setDays(tf.days)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${days === tf.days ? "bg-white/10 text-white" : "text-zinc-500 hover:text-zinc-300"}`}
            >
              {t(tf.key)}
            </button>
          ))}
        </div>
        <PriceChart prices={prices} vs={vs} days={days} />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {stats.map((s) => (
          <div key={s.label} className="rounded-lg border border-white/[6%] bg-white/[2%] p-3">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">{s.label}</div>
            <div className="mt-0.5 text-sm font-semibold text-zinc-100 tabular-nums">{s.value}</div>
          </div>
        ))}
      </div>

      {coin.description && (
        <p className="text-xs text-zinc-500 leading-relaxed">
          {coin.description}
          {coin.description.length >= 500 ? "…" : ""}
        </p>
      )}
    </div>
  )
}
