import { X } from "lucide-react"
import { Link } from "react-router-dom"
import { fmtPct, fmtPrice, trendClass } from "../format"
import type { MarketRow } from "../types"
import { Sparkline } from "./Sparkline"

interface Props {
  row: MarketRow
  vs: string
  onRemove?: () => void
}

// Watchlist-Kachel: Preis groß, 24h farbig, 7-Tage-Sparkline. Klick → Detail.
export function PriceCard({ row, vs, onRemove }: Props) {
  const pos = (row.change_24h ?? 0) >= 0
  return (
    <Link
      to={`/cryptoboard/coin/${row.id}`}
      className="group block rounded-xl border border-white/[7%] bg-white/[2%] hover:bg-white/[4%] hover:border-white/[12%] transition-colors p-3"
    >
      <div className="flex items-center gap-2">
        {row.image && <img src={row.image} alt="" className="w-6 h-6 rounded-full" />}
        <div className="min-w-0">
          <div className="text-sm font-medium text-zinc-100 truncate">{row.name}</div>
          <div className="text-[10px] text-zinc-500 font-mono uppercase">{row.symbol}</div>
        </div>
        {onRemove && (
          <button
            onClick={(e) => { e.preventDefault(); onRemove() }}
            className="ml-auto opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-rose-400 transition-all"
            aria-label="remove"
          >
            <X size={14} />
          </button>
        )}
      </div>
      <div className="mt-2 flex items-end justify-between gap-2">
        <div>
          <div className="text-lg font-semibold text-zinc-50 tabular-nums">{fmtPrice(row.price, vs)}</div>
          <div className={`text-xs font-mono tabular-nums ${trendClass(row.change_24h)}`}>{fmtPct(row.change_24h)}</div>
        </div>
        <div className="w-24">
          <Sparkline data={row.sparkline} positive={pos} />
        </div>
      </div>
    </Link>
  )
}
