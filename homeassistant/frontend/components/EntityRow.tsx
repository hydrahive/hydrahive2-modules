import { Star } from "lucide-react"
import type { HAState } from "../api"
import { displayState, isOn, isToggleable } from "../entityControl"

interface Props {
  entity: HAState
  isFavorite: boolean
  busy: boolean
  onToggle: (e: HAState) => void
  onToggleFavorite: (entityId: string) => void
}

export function EntityRow({ entity, isFavorite, busy, onToggle, onToggleFavorite }: Props) {
  const on = isOn(entity)
  const toggleable = isToggleable(entity)

  return (
    <div className="flex items-center gap-3 rounded-lg border border-white/8 bg-zinc-900/60 px-4 py-2.5">
      <button
        onClick={() => onToggleFavorite(entity.entity_id)}
        className="shrink-0 text-zinc-500 hover:text-amber-400 transition-colors"
        title={isFavorite ? "Aus Favoriten" : "Zu Favoriten"}
      >
        <Star size={15} fill={isFavorite ? "currentColor" : "none"}
          className={isFavorite ? "text-amber-400" : ""} />
      </button>

      <div className="min-w-0 flex-1">
        <div className="truncate text-sm text-zinc-100">{entity.name}</div>
        <div className="truncate text-[11px] text-zinc-500">{entity.entity_id}</div>
      </div>

      <div className={`shrink-0 text-sm tabular-nums ${on ? "text-emerald-400" : "text-zinc-400"}`}>
        {displayState(entity)}
      </div>

      {toggleable && (
        <button
          onClick={() => onToggle(entity)}
          disabled={busy}
          className={`shrink-0 relative h-6 w-11 rounded-full transition-colors disabled:opacity-40 ${
            on ? "bg-emerald-500/80" : "bg-zinc-700"
          }`}
          title={on ? "Ausschalten" : "Einschalten"}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-all ${
              on ? "left-[22px]" : "left-0.5"
            }`}
          />
        </button>
      )}
    </div>
  )
}
