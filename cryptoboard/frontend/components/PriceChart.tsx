import { useId } from "react"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { fmtPrice } from "../format"

interface Props {
  prices: [number, number][]
  vs: string
  days: string
}

// Großer Coin-Chart: gefüllte Fläche mit Verlaufs-Gradient, Farbe nach Trend.
export function PriceChart({ prices, vs, days }: Props) {
  const gid = useId().replace(/:/g, "")
  if (!prices || prices.length < 2) {
    return <div className="h-72 grid place-items-center text-sm text-zinc-600">—</div>
  }
  const data = prices.map(([ts, p]) => ({ ts, p }))
  const positive = data[data.length - 1].p >= data[0].p
  const color = positive ? "#34d399" : "#fb7185"

  const showTime = days === "1"
  const fmtTick = (ts: number) => {
    const d = new Date(ts)
    return showTime
      ? d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })
      : d.toLocaleDateString(undefined, { day: "2-digit", month: "2-digit" })
  }

  return (
    <ResponsiveContainer width="100%" height={288}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis
          dataKey="ts" tickFormatter={fmtTick} minTickGap={48}
          tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false}
        />
        <YAxis
          dataKey="p" domain={["dataMin", "dataMax"]} orientation="right" width={64}
          tickFormatter={(v) => fmtPrice(v, vs)}
          tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false}
        />
        <Tooltip
          contentStyle={{ background: "#18181b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
          labelStyle={{ color: "#a1a1aa" }}
          labelFormatter={(ts) => new Date(ts as number).toLocaleString()}
          formatter={(value) => [fmtPrice(Number(value), vs), ""] as [string, string]}
        />
        <Area type="monotone" dataKey="p" stroke={color} strokeWidth={2} fill={`url(#${gid})`} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}
