import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

export interface CompareSeries {
  id: string
  label: string
  color: string
  prices: [number, number][]   // [ts, price]
}

interface Props {
  series: CompareSeries[]
}

// Mehrere Coins normalisiert (% seit Start) auf einer gemeinsamen Zeitachse.
// Normalisierung erlaubt den Vergleich unabhängig vom absoluten Preisniveau.
export function CompareChart({ series }: Props) {
  const valid = series.filter((s) => s.prices.length >= 2)
  if (valid.length === 0) {
    return <div className="h-72 grid place-items-center text-sm text-zinc-600">—</div>
  }

  // Gemeinsame Zeitstempel-Map: index → { ts, <id>: pct }
  const rows = new Map<number, Record<string, number>>()
  for (const s of valid) {
    const base = s.prices[0][1]
    for (const [ts, p] of s.prices) {
      const pct = base ? ((p - base) / base) * 100 : 0
      const row = rows.get(ts) ?? { ts }
      row[s.id] = pct
      rows.set(ts, row)
    }
  }
  const data = [...rows.values()].sort((a, b) => a.ts - b.ts)
  const fmtDate = (ts: number) => new Date(ts).toLocaleDateString(undefined, { day: "2-digit", month: "2-digit" })

  return (
    <ResponsiveContainer width="100%" height={288}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis dataKey="ts" tickFormatter={fmtDate} minTickGap={48} tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis orientation="right" width={56} tickFormatter={(v) => `${v >= 0 ? "+" : ""}${Number(v).toFixed(0)}%`}
          tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: "#18181b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
          labelFormatter={(ts) => new Date(ts as number).toLocaleDateString()}
          formatter={(value, name) => [`${Number(value) >= 0 ? "+" : ""}${Number(value).toFixed(2)}%`, name] as [string, string]}
        />
        {valid.map((s) => (
          <Line key={s.id} type="monotone" dataKey={s.id} name={s.label} stroke={s.color}
            strokeWidth={1.8} dot={false} isAnimationActive={false} connectNulls />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
