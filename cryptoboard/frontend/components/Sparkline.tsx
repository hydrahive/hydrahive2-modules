import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts"

interface Props {
  data: number[]
  positive: boolean
  height?: number
}

// Winziger 7-Tage-Verlauf für Watchlist-/Coin-Kacheln. Bewusst achsen-/tooltip-los.
export function Sparkline({ data, positive, height = 32 }: Props) {
  if (!data || data.length < 2) return <div style={{ height }} />
  const points = data.map((v, i) => ({ i, v }))
  const color = positive ? "#34d399" : "#fb7185"
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={points} margin={{ top: 2, bottom: 2, left: 0, right: 0 }}>
        <YAxis hide domain={["dataMin", "dataMax"]} />
        <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
