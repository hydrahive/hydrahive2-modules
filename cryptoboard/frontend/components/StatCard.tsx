import { trendClass } from "../format"

interface Props {
  label: string
  value: string
  sub?: string | null
  trend?: number | null   // färbt sub grün/rot wenn gesetzt
}

// Kennzahl-Kachel für die Auswertung (aktueller Wert, ATH, Änderungen).
export function StatCard({ label, value, sub, trend }: Props) {
  return (
    <div className="rounded-xl border border-white/[6%] bg-white/[3%] px-4 py-3">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="mt-0.5 text-lg font-bold tabular-nums text-zinc-100">{value}</div>
      {sub != null && (
        <div className={`text-xs tabular-nums ${trend == null ? "text-zinc-500" : trendClass(trend)}`}>{sub}</div>
      )}
    </div>
  )
}
