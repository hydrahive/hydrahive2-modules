import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { miningApi } from "../api"
import { chartRows, latestTotalEur, perCard, seriesFor, type HistoryResponse, type Metric } from "../history"

const METRICS: Metric[] = ["eur", "pct", "watt", "temp"]
const RANGES = [24, 168] as const
const POLL_MS = 60_000
const tab = "rounded-md px-2 py-1 text-xs"

function fmt(metric: Metric, v: number): string {
  if (metric === "eur") return `${v.toFixed(2)} €`
  if (metric === "pct") return `${v.toFixed(0)} %`
  if (metric === "watt") return `${v.toFixed(0)} W`
  return `${v.toFixed(0)} °C`
}

/** Verlauf aller Rechner/Karten in einer Box, jede Linie eigene Farbe. */
export function HistoryChart() {
  const { t } = useTranslation("mining")
  const [metric, setMetric] = useState<Metric>("eur")
  const [hours, setHours] = useState<number>(24)
  const [data, setData] = useState<HistoryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const load = () => miningApi.history(hours)
      .then((d) => { if (alive) { setData(d); setError(null) } })
      .catch((e) => { if (alive) setError(String(e)) })
    load()
    const id = window.setInterval(load, POLL_MS)
    return () => { alive = false; window.clearInterval(id) }
  }, [hours])

  const series = useMemo(() => (data ? seriesFor(data.rigs, metric) : []), [data, metric])
  const rows = useMemo(() => (data ? chartRows(data, metric) : []), [data, metric])
  const total = data ? latestTotalEur(data) : null
  const fmtTime = (ts: number) => new Date(ts).toLocaleString(undefined, hours > 24
    ? { day: "2-digit", month: "2-digit", hour: "2-digit" } : { hour: "2-digit", minute: "2-digit" })

  return (
    <section className="space-y-3 rounded-xl border border-white/10 bg-zinc-900/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-zinc-200">
          {t("history_title")}
          {total !== null && <span className="ml-2 font-normal text-emerald-300">{t("history_total", { v: total.toFixed(2) })}</span>}
        </h2>
        <div className="flex flex-wrap gap-1">
          {METRICS.map((m) => (
            <button key={m} onClick={() => setMetric(m)}
              className={`${tab} ${metric === m ? "bg-emerald-600 text-white" : "text-zinc-400 hover:bg-white/10"}`}>
              {t(`history_m_${m}`)}
            </button>
          ))}
          <span className="mx-1 w-px bg-white/10" />
          {RANGES.map((h) => (
            <button key={h} onClick={() => setHours(h)}
              className={`${tab} ${hours === h ? "bg-zinc-700 text-white" : "text-zinc-400 hover:bg-white/10"}`}>
              {t(`history_r_${h}`)}
            </button>
          ))}
        </div>
      </div>
      {error && <div className="text-xs text-rose-300">{error}</div>}
      {!perCard(metric) && <p className="text-xs text-zinc-500">{t("history_per_rig_hint")}</p>}
      {rows.length < 2 ? (
        <div className="grid h-64 place-items-center text-sm text-zinc-500">{t("history_empty")}</div>
      ) : (
        <ResponsiveContainer width="100%" height={288}>
          <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="ts" type="number" scale="time" domain={["dataMin", "dataMax"]} tickFormatter={fmtTime}
              minTickGap={48} tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis orientation="right" width={60} tickFormatter={(v) => fmt(metric, Number(v))}
              tick={{ fill: "#71717a", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: "#18181b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
              labelFormatter={(ts) => new Date(ts as number).toLocaleString()}
              formatter={(v, name, item) => {
                const coin = (item?.payload as Record<string, unknown>)?.[`${String(item?.dataKey)}:coin`]
                return [`${fmt(metric, Number(v))}${coin ? ` · ${String(coin).toUpperCase()}` : ""}`, name] as [string, string]
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11, color: "#a1a1aa" }} />
            {series.map((s, i) => (
              <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color}
                strokeDasharray={i >= 12 ? "4 3" : undefined}
                strokeWidth={1.8} dot={false} isAnimationActive={false} connectNulls={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </section>
  )
}
