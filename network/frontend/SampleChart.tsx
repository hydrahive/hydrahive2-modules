import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { useTranslation } from "react-i18next"
import { chartPoints, type Sample } from "./logic"
import { CHART } from "./ui"
import { hourLabel } from "./when"

/** Antwortzeit (Linie) und Verlust (Balken) der eigenen Messung. */
export function SampleChart({ samples }: { samples: Sample[] }) {
  const { t } = useTranslation("network")
  if (samples.length < 2) return <p className="text-sm text-[#c8d2df]">{t("no_samples")}</p>
  const data = chartPoints(samples)
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" />
          <XAxis dataKey="ts" tickFormatter={hourLabel} stroke={CHART.axis} fontSize={11} minTickGap={40} />
          <YAxis yAxisId="rtt" stroke={CHART.axis} fontSize={11} width={40} />
          <YAxis yAxisId="loss" orientation="right" domain={[0, 100]} stroke={CHART.axis} fontSize={11} width={32} />
          <Tooltip labelFormatter={(v) => hourLabel(Number(v))} contentStyle={{ background: "rgb(21 28 43)", border: "1px solid rgb(42 54 75)" }} />
          <Bar yAxisId="loss" dataKey="loss" name={t("chart.loss")} fill={CHART.loss} isAnimationActive={false} />
          <Line yAxisId="rtt" dataKey="rtt" name={t("chart.rtt")} stroke={CHART.rtt} dot={false} strokeWidth={1.5} isAnimationActive={false} connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
