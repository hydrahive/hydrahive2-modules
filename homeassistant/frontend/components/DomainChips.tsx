import { Star } from "lucide-react"
import { moduleIcon } from "@/shared/module-icon"
import { domainLabel, domainIcon, sortDomains } from "../entityControl"
import type { HAState } from "../api"

interface Props {
  states: HAState[]
  favCount: number
  active: string | null // null = alle, "__fav__" = Favoriten, sonst domain
  onSelect: (key: string | null) => void
}

export function DomainChips({ states, favCount, active, onSelect }: Props) {
  // Anzahl je Domain zählen
  const counts = new Map<string, number>()
  for (const s of states) counts.set(s.domain, (counts.get(s.domain) ?? 0) + 1)
  const domains = sortDomains([...counts.keys()])

  const chip = (key: string | null, label: string, count: number, IconEl: React.ReactNode) => {
    const isActive = active === key
    return (
      <button
        key={key ?? "all"}
        onClick={() => onSelect(key)}
        className={`flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-colors ${
          isActive
            ? "border-sky-400/40 bg-sky-500/20 text-sky-200"
            : "border-white/10 bg-zinc-800/60 text-zinc-300 hover:bg-zinc-700/60"
        }`}
      >
        {IconEl}
        <span>{label}</span>
        <span className={isActive ? "text-sky-300/80" : "text-zinc-500"}>{count}</span>
      </button>
    )
  }

  return (
    <div className="flex flex-wrap gap-2">
      {chip(null, "Alle", states.length, null)}
      {favCount > 0 &&
        chip("__fav__", "Favoriten", favCount,
          <Star size={13} className="text-amber-400" fill="currentColor" />)}
      {domains.map((d) => {
        const Icon = moduleIcon(domainIcon(d))
        return chip(d, domainLabel(d), counts.get(d) ?? 0, <Icon size={13} />)
      })}
    </div>
  )
}
