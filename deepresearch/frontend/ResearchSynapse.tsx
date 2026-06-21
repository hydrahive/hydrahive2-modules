import { useMemo } from "react"

interface ResearchSynapseProps {
  round: number
  totalSources: number
  phase: string
}

const VIEW_W = 520
const VIEW_H = 220
const CX = 92
const CY = 110
const ARM = 78

/** Lebendige Knoten-Graph-Visualisierung: Query-Kern → Runden-Knoten → Quell-Blätter.
 *  Akzent über var(--accent) → folgt dem App-Theme. */
export function ResearchSynapse({ round, totalSources, phase }: ResearchSynapseProps) {
  const done = phase === "done"
  const accent = done ? "#46c97e" : "var(--accent, #e0795e)"
  const rounds = Math.max(1, round)

  const roundNodes = useMemo(() => {
    return Array.from({ length: rounds }, (_, i) => {
      const t = rounds === 1 ? 0.5 : i / (rounds - 1)
      const angle = (-52 + t * 104) * (Math.PI / 180)
      return { x: CX + ARM * Math.cos(angle), y: CY + ARM * Math.sin(angle), label: `R${i + 1}` }
    })
  }, [rounds])

  const last = roundNodes[roundNodes.length - 1]
  const leaves = useMemo(() => {
    const n = Math.min(totalSources, 28)
    return Array.from({ length: n }, (_, i) => {
      const ring = 1 + Math.floor(i / 7)
      const a = ((i % 7) / 7) * Math.PI * 2 + i * 0.6
      return { x: last.x + ring * 15 * Math.cos(a), y: last.y + ring * 15 * Math.sin(a), key: i }
    })
  }, [totalSources, last.x, last.y])

  return (
    <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="w-full h-44" role="img" aria-label="Recherche-Visualisierung">
      <style>{`
        @keyframes dr-pop{0%{transform:scale(0);opacity:0}60%{transform:scale(1.3)}100%{transform:scale(1);opacity:1}}
        .dr-leaf{transform-box:fill-box;transform-origin:center;animation:dr-pop .5s cubic-bezier(.2,1,.3,1) both}
        .dr-rn{transform-box:fill-box;transform-origin:center;animation:dr-pop .45s cubic-bezier(.2,1,.3,1) both}
        @media (prefers-reduced-motion:reduce){.dr-leaf,.dr-rn{animation:none}}
      `}</style>

      {roundNodes.map((n, i) => (
        <line key={`e${i}`} x1={CX} y1={CY} x2={n.x} y2={n.y} stroke={accent} strokeOpacity="0.35" strokeWidth="1.2" />
      ))}
      {leaves.map((l) => (
        <line key={`le${l.key}`} x1={last.x} y1={last.y} x2={l.x} y2={l.y} stroke={accent} strokeOpacity="0.18" strokeWidth="0.8" />
      ))}
      {leaves.map((l) => (
        <circle key={`l${l.key}`} className="dr-leaf" cx={l.x} cy={l.y} r="3" fill={accent} fillOpacity="0.85" />
      ))}
      {roundNodes.map((n, i) => (
        <g key={`r${i}`} className="dr-rn">
          <circle cx={n.x} cy={n.y} r="8" fill="#15141a" stroke={accent} strokeWidth="1.5" />
          <text x={n.x} y={n.y + 2.6} textAnchor="middle" fontSize="7.5" fill={accent} fontFamily="ui-monospace,monospace">
            {n.label}
          </text>
        </g>
      ))}

      {!done && (
        <circle cx={CX} cy={CY} fill="none" stroke={accent} strokeWidth="1.5">
          <animate attributeName="r" from="12" to="48" dur="2s" repeatCount="indefinite" />
          <animate attributeName="opacity" from="0.5" to="0" dur="2s" repeatCount="indefinite" />
        </circle>
      )}
      <circle cx={CX} cy={CY} r="12" fill={accent} />
      <circle cx={CX} cy={CY} r="12" fill="none" stroke="#15141a" strokeWidth="2" strokeOpacity="0.3" />
    </svg>
  )
}
