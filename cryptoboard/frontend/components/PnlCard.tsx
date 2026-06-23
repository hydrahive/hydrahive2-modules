import { trendClass } from "../format"

interface Props {
  label: string
  value: string
  sub?: string | null
  trend?: number | null   // färbt value grün/rot wenn gesetzt
}

// Kompakte Kennzahl-Kachel für die Portfolio-Summary (Gesamtwert, P&L, …).
export function PnlCard({ label, value, sub, trend }: Props) {
  const color = trend == null ? "text-zinc-100" : trendClass(trend)
  return (
    <div className="rounded-xl border border-white/[6%] bg-white/[3%] px-4 py-3">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className={`mt-0.5 text-lg font-bold tabular-nums ${color}`}>{value}</div>
      {sub != null && <div className={`text-xs tabular-nums ${trend == null ? "text-zinc-500" : trendClass(trend)}`}>{sub}</div>}
    </div>
  )
}
