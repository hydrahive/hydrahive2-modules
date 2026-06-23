import { useMemo } from "react"
import type { Position } from "../types"

interface Props {
  positions: Position[]   // nur offene erwartet
}

// Stabile Farbpalette für Segmente (zyklisch).
const PALETTE = [
  "#34d399", "#60a5fa", "#f472b6", "#fbbf24", "#a78bfa",
  "#fb923c", "#22d3ee", "#f87171", "#4ade80", "#c084fc",
]

// Allocation-Donut (reines SVG, kein Chart-Lib). Zeigt die größten Positionen,
// fasst den Rest zu „Sonstige" zusammen.
export function AllocationDonut({ positions }: Props) {
  const R = 42
  const CIRC = 2 * Math.PI * R

  // Segmente inkl. vorberechnetem Dash-Offset (kein Reassign während Render).
  const segments = useMemo(() => {
    const open = positions.filter((p) => p.is_open && p.value > 0)
    const sorted = [...open].sort((a, b) => b.value - a.value)
    const top = sorted.slice(0, 9)
    const restPct = sorted.slice(9).reduce((s, p) => s + p.allocation, 0)
    const base = top.map((p, i) => ({ label: p.symbol || p.coin_id, pct: p.allocation, color: PALETTE[i % PALETTE.length] }))
    const items = restPct > 0.01 ? [...base, { label: "···", pct: restPct, color: "#52525b" }] : base

    // Kumulative Offsets vorab via reduce (kein mutierender Zustand im Render).
    return items.reduce<{ label: string; pct: number; color: string; len: number; offset: number }[]>((acc, s) => {
      const len = (s.pct / 100) * CIRC
      const offset = acc.length ? acc[acc.length - 1].offset + acc[acc.length - 1].len : 0
      return [...acc, { ...s, len, offset }]
    }, [])
  }, [positions, CIRC])

  if (segments.length === 0) return null

  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 100 100" className="w-28 h-28 -rotate-90 shrink-0">
        {segments.map((s, i) => (
          <circle key={i} cx="50" cy="50" r={R} fill="none" stroke={s.color}
            strokeWidth="12" strokeDasharray={`${s.len} ${CIRC - s.len}`} strokeDashoffset={-s.offset} />
        ))}
      </svg>
      <ul className="space-y-1 text-xs">
        {segments.map((s, i) => (
          <li key={i} className="flex items-center gap-2 tabular-nums">
            <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: s.color }} />
            <span className="text-zinc-300 font-medium">{s.label}</span>
            <span className="text-zinc-500">{s.pct.toFixed(1)} %</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
