import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts"
import { cryptoApi } from "../api"
import type { IndicatorData } from "../types"

interface Props {
  coinId: string
  vs: string
}

interface Point {
  ts: number
  price: number
  sma20: number | null
  sma50: number | null
  rsi: number | null
  macd: number | null
  signal: number | null
  hist: number | null
}

const AXIS = { fill: "#71717a", fontSize: 10 }
const GRID = "rgba(255,255,255,0.05)"
const TOOLTIP = { background: "#18181b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 11 }

// Technische Indikatoren unter dem Coin-Chart: Preis+SMA, RSI(14), MACD(12/26/9).
export function IndicatorPanel({ coinId, vs }: Props) {
  const { t } = useTranslation("cryptoboard")
  const [data, setData] = useState<IndicatorData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    cryptoApi.indicators(coinId, "90", vs)
      .then((d) => { if (alive) setData(d) })
      .catch(() => {})
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [coinId, vs])

  if (loading) return <p className="text-xs text-zinc-500 py-4 text-center">{t("loading")}</p>
  if (!data || data.prices.length < 2) return <p className="text-xs text-zinc-600 py-4 text-center">—</p>

  const points: Point[] = data.times.map((ts, i) => ({
    ts,
    price: data.prices[i],
    sma20: data.sma20[i],
    sma50: data.sma50[i],
    rsi: data.rsi14[i],
    macd: data.macd[i],
    signal: data.macd_signal[i],
    hist: data.macd_histogram[i],
  }))

  const fmtDate = (ts: number) => new Date(ts).toLocaleDateString(undefined, { day: "2-digit", month: "2-digit" })

  return (
    <div className="space-y-4">
      {/* Preis + gleitende Durchschnitte */}
      <Section title={t("ind_price_ma")}>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
            <XAxis dataKey="ts" tickFormatter={fmtDate} minTickGap={48} tick={AXIS} axisLine={false} tickLine={false} />
            <YAxis dataKey="price" domain={["dataMin", "dataMax"]} orientation="right" width={56} tick={AXIS} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP} labelFormatter={(ts) => new Date(ts as number).toLocaleDateString()} />
            <Line type="monotone" dataKey="price" stroke="#e4e4e7" strokeWidth={1.5} dot={false} isAnimationActive={false} name={t("ind_price")} />
            <Line type="monotone" dataKey="sma20" stroke="#60a5fa" strokeWidth={1} dot={false} isAnimationActive={false} name="SMA20" connectNulls />
            <Line type="monotone" dataKey="sma50" stroke="#f472b6" strokeWidth={1} dot={false} isAnimationActive={false} name="SMA50" connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </Section>

      {/* RSI */}
      <Section title={t("ind_rsi")}>
        <ResponsiveContainer width="100%" height={110}>
          <LineChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
            <XAxis dataKey="ts" tickFormatter={fmtDate} minTickGap={48} tick={AXIS} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} ticks={[30, 50, 70]} orientation="right" width={56} tick={AXIS} axisLine={false} tickLine={false} />
            <ReferenceLine y={70} stroke="#f43f5e" strokeDasharray="3 3" strokeOpacity={0.5} />
            <ReferenceLine y={30} stroke="#34d399" strokeDasharray="3 3" strokeOpacity={0.5} />
            <Tooltip contentStyle={TOOLTIP} labelFormatter={(ts) => new Date(ts as number).toLocaleDateString()} />
            <Line type="monotone" dataKey="rsi" stroke="#a78bfa" strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls name="RSI" />
          </LineChart>
        </ResponsiveContainer>
      </Section>

      {/* MACD */}
      <Section title={t("ind_macd")}>
        <ResponsiveContainer width="100%" height={110}>
          <BarChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
            <XAxis dataKey="ts" tickFormatter={fmtDate} minTickGap={48} tick={AXIS} axisLine={false} tickLine={false} />
            <YAxis orientation="right" width={56} tick={AXIS} axisLine={false} tickLine={false} />
            <ReferenceLine y={0} stroke="#52525b" />
            <Tooltip contentStyle={TOOLTIP} labelFormatter={(ts) => new Date(ts as number).toLocaleDateString()} />
            <Bar dataKey="hist" fill="#52525b" isAnimationActive={false} name="Histogram" />
            <Line type="monotone" dataKey="macd" stroke="#60a5fa" strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls name="MACD" />
            <Line type="monotone" dataKey="signal" stroke="#fb923c" strokeWidth={1} dot={false} isAnimationActive={false} connectNulls name="Signal" />
          </BarChart>
        </ResponsiveContainer>
      </Section>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] font-medium text-zinc-400 mb-1 px-1">{title}</div>
      {children}
    </div>
  )
}
