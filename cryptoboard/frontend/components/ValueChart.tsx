import { useId } from "react"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { fmtCompact, fmtPrice } from "../format"
import type { ValuePoint } from "../types"

interface Props {
  points: ValuePoint[]
  vs?: string
}

// Portfolio-Gesamtwert über die Zeit (Flächen-Chart, reiner Marktwert in EUR).
export function ValueChart({ points, vs = "eur" }: Props) {
  const gid = useId().replace(/:/g, "")
  if (!points || points.length < 2) {
    return <div className="h-72 grid place-items-center text-sm text-zinc-600">—</div>
  }
  const data = points.map((p) => ({ ts: new Date(p.day).getTime(), v: p.value }))
  const positive = data[data.length - 1].v >= data[0].v
  const color = positive ? "#34d399" : "#fb7185"

  const fmtTick = (ts: number) => {
    const d = new Date(ts)
    return d.toLocaleDateString(undefined, { month: "short", year: "2-digit" })
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis dataKey="ts" type="number" scale="time" domain={["dataMin", "dataMax"]}
          tickFormatter={fmtTick} minTickGap={60}
          tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis dataKey="v" orientation="right" width={64} tickFormatter={(v) => fmtCompact(v, vs)}
          tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: "#18181b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "#a1a1aa" }}
          labelFormatter={(ts) => new Date(ts as number).toLocaleDateString()}
          formatter={(value) => [fmtPrice(Number(value), vs), "Wert"] as [string, string]}
        />
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={2} fill={`url(#${gid})`} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
