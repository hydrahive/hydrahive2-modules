import { useMemo } from "react"

interface ResearchSynapseProps {
  round: number
  totalSources: number
  phase: string
  query?: string
}

const W = 520
const H = 220
const CX = W / 2
const CY = H / 2
const ARM = 78 // Radius der Runden-Knoten um das Zentrum
const MAX_SUBS = 10
const MAX_LEAVES = 40

/** Ausbalancierter Knoten-Graph (nach odysseus' researchSynapse):
 *  Query-Kern im Zentrum → Runden-Knoten um den GANZEN Kreis verteilt →
 *  Quellen pro Runde in sauberen Bögen an ihrem Knoten. Akzent folgt --accent. */
export function ResearchSynapse({ round, totalSources, phase, query }: ResearchSynapseProps) {
  const done = phase === "done"
  const accent = done ? "#46c97e" : "var(--accent, #b8543a)"
  const rounds = Math.min(Math.max(1, round), MAX_SUBS)

  const subs = useMemo(() => {
    const slots = Math.max(6, rounds)
    return Array.from({ length: rounds }, (_, i) => {
      const angle = (i / slots) * Math.PI * 2 - Math.PI / 2
      return { x: CX + Math.cos(angle) * ARM, y: CY + Math.sin(angle) * ARM, label: `R${i + 1}` }
    })
  }, [rounds])

  // Quellen rund-robin über die Runden-Knoten verteilen → balanciert, kein Klumpen.
  const leaves = useMemo(() => {
    const n = Math.min(totalSources, MAX_LEAVES)
    const perSub: number[] = new Array(subs.length).fill(0)
    const out: { x: number; y: number; sx: number; sy: number; key: number }[] = []
    for (let s = 0; s < n; s++) {
      const si = s % subs.length
      const sub = subs[si]
      const idx = perSub[si]++
      const ring = Math.floor(idx / 6)
      const slot = idx % 6
      const baseAngle = Math.atan2(sub.y - CY, sub.x - CX)
      const angle = baseAngle + (slot - 2.5) * (2.4 / 6)
      const r = 26 + ring * 14
      out.push({ x: sub.x + Math.cos(angle) * r, y: sub.y + Math.sin(angle) * r, sx: sub.x, sy: sub.y, key: s })
    }
    return out
  }, [totalSources, subs])

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-48" role="img" aria-label="Recherche-Visualisierung">
      <style>{`
        @keyframes dr-pop{0%{transform:scale(0);opacity:0}60%{transform:scale(1.25)}100%{transform:scale(1);opacity:1}}
        .dr-n{transform-box:fill-box;transform-origin:center;animation:dr-pop .42s cubic-bezier(.2,1,.3,1) both}
        @media (prefers-reduced-motion:reduce){.dr-n{animation:none}}
      `}</style>

      {subs.map((n, i) => (
        <line key={`se${i}`} x1={CX} y1={CY} x2={n.x} y2={n.y} stroke={accent} strokeOpacity="0.4" strokeWidth="1.2" />
      ))}
      {leaves.map((l) => (
        <line key={`le${l.key}`} x1={l.sx} y1={l.sy} x2={l.x} y2={l.y} stroke={accent} strokeOpacity="0.18" strokeWidth="0.8" />
      ))}
      {leaves.map((l) => (
        <circle key={`l${l.key}`} className="dr-n" cx={l.x} cy={l.y} r="3.2" fill={accent} fillOpacity="0.85" />
      ))}
      {subs.map((n, i) => (
        <g key={`s${i}`} className="dr-n">
          <circle cx={n.x} cy={n.y} r="7.5" fill="#15141a" stroke={accent} strokeWidth="1.6" />
          <text x={n.x} y={n.y + 2.6} textAnchor="middle" fontSize="7.5" fill={accent} fontFamily="ui-monospace,monospace">
            {n.label}
          </text>
        </g>
      ))}

      {!done && (
        <circle cx={CX} cy={CY} fill="none" stroke={accent} strokeWidth="1.5">
          <animate attributeName="r" from="12" to="46" dur="2s" repeatCount="indefinite" />
          <animate attributeName="opacity" from="0.5" to="0" dur="2s" repeatCount="indefinite" />
        </circle>
      )}
      <circle cx={CX} cy={CY} r="11" fill={accent} />
      {query && (
        <text x={CX} y={CY + 30} textAnchor="middle" fontSize="9" fill="var(--accent,#b8543a)" fillOpacity="0.7" fontFamily="ui-monospace,monospace">
          {query.length > 30 ? query.slice(0, 29) + "…" : query}
        </text>
      )}
    </svg>
  )
}
