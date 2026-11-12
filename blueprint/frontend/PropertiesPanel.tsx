import { Trash2 } from "lucide-react"
import { labelOf, hasPlaceholder } from "./palette-data"
import { SIDE_PANEL } from "./styles"
import type { T } from "./texts.de"
import type { BPNode } from "./types"

interface Props {
  node: BPNode | undefined
  /** In der Vorschau des Vorschlags lässt sich nichts bearbeiten. */
  preview: boolean
  t: T
  onChange: (patch: Partial<BPNode["data"]>) => void
  onDelete: () => void
}

const field = "w-full rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] px-3 py-2 text-sm text-[#e8eef8] placeholder-[#9aa7bc] focus:outline-none focus:ring-1 focus:ring-[rgb(var(--hh-s-rand-hover,70_97_127))]"
const lbl = "block text-[11px] font-medium uppercase tracking-wide text-[#9aa7bc] mb-1"

export function PropertiesPanel({ node, preview, t, onChange, onDelete }: Props) {
  if (!node || preview) {
    return (
      <div className={`${SIDE_PANEL} p-4`}>
        <p className="text-sm text-[#9aa7bc]">{t(preview ? "panel_preview" : "panel_empty")}</p>
      </div>
    )
  }

  const d = node.data
  return (
    <div className={`${SIDE_PANEL} space-y-3 overflow-y-auto p-4`}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[#9aa7bc]">
          {labelOf(d.subtype)}
        </span>
        <button
          onClick={onDelete}
          className="text-[#9aa7bc] hover:text-red-400 transition-colors"
          title={t("panel_delete")}
          aria-label={t("panel_delete")}
        >
          <Trash2 size={15} />
        </button>
      </div>

      <div>
        <label className={lbl}>{t("panel_label")}</label>
        <input
          value={d.label}
          onChange={(e) => onChange({ label: e.target.value })}
          placeholder={t("panel_label_placeholder")}
          className={field}
          autoFocus
        />
      </div>

      {hasPlaceholder(d.subtype) && (
        <div>
          <label className={lbl}>{t("panel_placeholder")}</label>
          <input
            value={d.placeholder ?? ""}
            onChange={(e) => onChange({ placeholder: e.target.value })}
            placeholder={t("panel_placeholder_placeholder")}
            className={field}
          />
        </div>
      )}

      <div>
        <label className={lbl}>{t("panel_note")}</label>
        <textarea
          value={d.note}
          onChange={(e) => onChange({ note: e.target.value })}
          placeholder={t("panel_note_placeholder")}
          rows={4}
          className={`${field} resize-y`}
        />
      </div>
    </div>
  )
}
