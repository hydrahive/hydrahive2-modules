import { Trash2 } from "lucide-react"
import { labelOf, hasPlaceholder } from "./palette-data"
import type { BPNode } from "./types"

interface Props {
  node: BPNode | undefined
  onChange: (patch: Partial<BPNode["data"]>) => void
  onDelete: () => void
}

const field = "w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-white/20"
const lbl = "block text-[11px] font-medium uppercase tracking-wide text-zinc-500 mb-1"

export function PropertiesPanel({ node, onChange, onDelete }: Props) {
  if (!node) {
    return (
      <div className="w-64 shrink-0 border-l border-white/8 bg-zinc-950/40 p-4">
        <p className="text-sm text-zinc-600">Baustein anklicken zum Bearbeiten.</p>
      </div>
    )
  }

  const d = node.data
  return (
    <div className="w-64 shrink-0 space-y-3 overflow-y-auto border-l border-white/8 bg-zinc-950/40 p-4">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">
          {labelOf(d.subtype)}
        </span>
        <button
          onClick={onDelete}
          className="text-zinc-500 hover:text-red-400 transition-colors"
          title="Baustein löschen"
        >
          <Trash2 size={15} />
        </button>
      </div>

      <div>
        <label className={lbl}>Beschriftung</label>
        <input
          value={d.label}
          onChange={(e) => onChange({ label: e.target.value })}
          placeholder="z.B. Speichern-Button"
          className={field}
          autoFocus
        />
      </div>

      {hasPlaceholder(d.subtype) && (
        <div>
          <label className={lbl}>Platzhalter</label>
          <input
            value={d.placeholder ?? ""}
            onChange={(e) => onChange({ placeholder: e.target.value })}
            placeholder="z.B. Name eingeben…"
            className={field}
          />
        </div>
      )}

      <div>
        <label className={lbl}>Notiz an den Agenten</label>
        <textarea
          value={d.note}
          onChange={(e) => onChange({ note: e.target.value })}
          placeholder="Was soll hier passieren / wie gemeint?"
          rows={4}
          className={`${field} resize-y`}
        />
      </div>
    </div>
  )
}
