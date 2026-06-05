import { Check, Plus } from "lucide-react"
import { Link } from "react-router-dom"
import { fmtPct, fmtPrice, trendClass } from "../format"
import type { MarketRow } from "../types"
import { Sparkline } from "./Sparkline"

interface Props {
  row: MarketRow
  vs: string
  watched: boolean
  onToggle: () => void
}

// Eine Zeile der Top-Coins-Liste — Rang, Coin, Preis, 24h/7d, Sparkline, Toggle.
export function CoinRow({ row, vs, watched, onToggle }: Props) {
  const pos = (row.change_24h ?? 0) >= 0
  return (
    <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-white/[3%] transition-colors">
      <span className="w-6 text-[11px] text-zinc-600 tabular-nums text-right shrink-0">{row.market_cap_rank ?? "—"}</span>
      <Link to={`/cryptoboard/coin/${row.id}`} className="flex items-center gap-2 min-w-0 flex-1">
        {row.image && <img src={row.image} alt="" className="w-5 h-5 rounded-full shrink-0" />}
        <span className="text-sm text-zinc-100 truncate">{row.name}</span>
        <span className="text-[10px] text-zinc-500 font-mono uppercase shrink-0">{row.symbol}</span>
      </Link>
      <span className="w-24 text-sm text-zinc-100 tabular-nums text-right shrink-0">{fmtPrice(row.price, vs)}</span>
      <span className={`w-16 text-xs font-mono tabular-nums text-right shrink-0 ${trendClass(row.change_24h)}`}>{fmtPct(row.change_24h)}</span>
      <span className={`hidden md:block w-16 text-xs font-mono tabular-nums text-right shrink-0 ${trendClass(row.change_7d)}`}>{fmtPct(row.change_7d)}</span>
      <span className="hidden lg:block w-20 shrink-0">
        <Sparkline data={row.sparkline} positive={pos} height={28} />
      </span>
      <button
        onClick={onToggle}
        className={`w-6 shrink-0 grid place-items-center transition-colors ${watched ? "text-emerald-400" : "text-zinc-600 hover:text-zinc-200"}`}
        aria-label={watched ? "watched" : "add"}
      >
        {watched ? <Check size={15} /> : <Plus size={15} />}
      </button>
    </div>
  )
}
