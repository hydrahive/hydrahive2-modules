import { useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { moduleIcon } from "@/shared/module-icon"
import { domainLabel, domainIcon } from "../entityControl"
import { EntityRow } from "./EntityRow"
import type { HAState } from "../api"

interface Props {
  domain: string
  entities: HAState[]
  favorites: Set<string>
  busy: Set<string>
  defaultOpen: boolean
  onToggle: (e: HAState) => void
  onToggleFavorite: (entityId: string) => void
}

export function DomainSection({
  domain, entities, favorites, busy, defaultOpen, onToggle, onToggleFavorite,
}: Props) {
  const [open, setOpen] = useState(defaultOpen)
  const Icon = moduleIcon(domainIcon(domain))

  return (
    <section className="rounded-xl border border-white/8 bg-zinc-900/40">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left hover:bg-white/5 transition-colors rounded-xl"
      >
        {open ? <ChevronDown size={16} className="text-zinc-500" />
              : <ChevronRight size={16} className="text-zinc-500" />}
        <Icon size={16} className="text-zinc-400" />
        <span className="text-sm font-medium text-zinc-200">{domainLabel(domain)}</span>
        <span className="ml-auto text-xs text-zinc-500">{entities.length}</span>
      </button>
      {open && (
        <div className="space-y-1.5 px-3 pb-3">
          {entities.map((e) => (
            <EntityRow
              key={e.entity_id}
              entity={e}
              isFavorite={favorites.has(e.entity_id)}
              busy={busy.has(e.entity_id)}
              onToggle={onToggle}
              onToggleFavorite={onToggleFavorite}
            />
          ))}
        </div>
      )}
    </section>
  )
}
