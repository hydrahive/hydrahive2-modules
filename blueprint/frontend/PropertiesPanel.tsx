import { Trash2 } from "lucide-react"
import { labelOf, hasPlaceholder } from "./palette-data"
import type { BPNode } from "./types"

interface Props {
  node: BPNode | undefined
  onChange: (patch: Partial<BPNode["data"]>) => void
  onDelete: () => void
}

const field = "w-full rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] px-3 py-2 text-sm text-[#e8eef8] placeholder-[#9aa7bc] focus:outline-none focus:ring-1 focus:ring-[rgb(var(--hh-s-rand-hover,70_97_127))]"
const lbl = "block text-[11px] font-medium uppercase tracking-wide text-[#9aa7bc] mb-1"

export function PropertiesPanel({ node, onChange, onDelete }: Props) {
  if (!node) {
    return (
      <div className="w-64 shrink-0 border-l border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32)/0.4)] p-4">
        <p className="text-sm text-[#9aa7bc]">Baustein anklicken zum Bearbeiten.</p>
      </div>
    )
  }

  const d = node.data
  return (
    <div className="w-64 shrink-0 space-y-3 overflow-y-auto border-l border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32)/0.4)] p-4">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[#9aa7bc]">
          {labelOf(d.subtype)}
        </span>
        <button
          onClick={onDelete}
          className="text-[#9aa7bc] hover:text-red-400 transition-colors"
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
