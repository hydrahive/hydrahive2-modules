import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { cryptoApi } from "../api"
import type { Sentiment } from "../types"

// Farbe nach Index-Wert: rot (Angst) → gelb → grün (Gier).
function colorFor(v: number): string {
  if (v < 25) return "#f43f5e"
  if (v < 45) return "#fb923c"
  if (v < 55) return "#fbbf24"
  if (v < 75) return "#a3e635"
  return "#34d399"
}

// Fear & Greed Index als Halbkreis-Gauge (reines SVG, kein Chart-Lib).
export function FearGreedGauge() {
  const { t } = useTranslation("cryptoboard")
  const [data, setData] = useState<Sentiment | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    cryptoApi.sentiment(1)
      .then((d) => { if (alive) setData(d) })
      .catch(() => {})
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  if (loading) return <p className="text-xs text-zinc-500 py-3 text-center">{t("loading")}</p>
  const v = data?.current?.value
  if (v == null) return <p className="text-xs text-zinc-500 py-3 text-center">{t("fng_unavailable")}</p>

  const R = 54
  const CIRC = Math.PI * R                 // Halbkreis-Länge
  const filled = (v / 100) * CIRC
  const color = colorFor(v)

  return (
    <div className="flex flex-col items-center py-2">
      <svg viewBox="0 0 130 72" className="w-44">
        {/* Hintergrund-Bogen */}
        <path d="M 11 65 A 54 54 0 0 1 119 65" fill="none" stroke="#27272a" strokeWidth="10" strokeLinecap="round" />
        {/* Wert-Bogen */}
        <path d="M 11 65 A 54 54 0 0 1 119 65" fill="none" stroke={color} strokeWidth="10"
          strokeLinecap="round" strokeDasharray={`${filled} ${CIRC}`} />
        <text x="65" y="55" textAnchor="middle" className="fill-zinc-100" style={{ fontSize: 22, fontWeight: 700 }}>{v}</text>
      </svg>
      <div className="text-sm font-medium -mt-1" style={{ color }}>{data?.current?.classification ?? "—"}</div>
      <div className="text-[10px] text-zinc-600 mt-0.5">{t("fng_title")}</div>
    </div>
  )
}
