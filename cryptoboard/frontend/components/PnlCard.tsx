import { trendClass } from "../format"

interface Props {
  label: string
  value: string
  sub?: string | null
  trend?: number | null   // färbt value grün/rot wenn gesetzt
}

// Kompakte Kennzahl-Kachel für die Portfolio-Summary (Gesamtwert, P&L, …).
export function PnlCard({ label, value, sub, trend }: Props) {
  const color = trend == null ? "text-[#e8eef8]" : trendClass(trend)
  return (
    <div className="rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-4 py-3">
      <div className="text-xs text-[#9aa7bc]">{label}</div>
      <div className={`mt-0.5 text-lg font-bold tabular-nums ${color}`}>{value}</div>
      {sub != null && <div className={`text-xs tabular-nums ${trend == null ? "text-[#9aa7bc]" : trendClass(trend)}`}>{sub}</div>}
    </div>
  )
}
