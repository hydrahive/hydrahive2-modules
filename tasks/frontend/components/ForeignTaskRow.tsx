import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { ForeignTask, ForeignTaskFull } from "../types"
import { ForeignBadge } from "./ForeignBadge"
import { ForeignDetail } from "./ForeignDetail"

interface Props {
  task: ForeignTask
  /** Nur für Tests: Detail aufgeklappt mit vorgegebenem Volltext. */
  initialOpen?: boolean
  initialFull?: ForeignTaskFull | null
}

// Zeile eines fremden Tasks: kein Abhaken, kein Statuswechsel, kein Löschen, kein Verschieben
// (Spec §Oberfläche: „gehört zu <instanz>“; Bearbeiten kommt mit G4). Klick klappt den Volltext auf.
export function ForeignTaskRow({ task, initialOpen = false, initialFull }: Props) {
  const { t } = useTranslation("tasks")
  const [open, setOpen] = useState(initialOpen)
  const isDone = task.status === "done" || task.status === "cancelled"
  const name = task.origin_name || task.origin_fp.slice(0, 12)

  return (
    <div
      data-testid="foreign-row"
      className={`px-2 py-1.5 rounded hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] transition-colors ${isDone ? "opacity-50" : ""} ${task.stale ? "opacity-70" : ""}`}
    >
      <button type="button" onClick={() => setOpen((v) => !v)} className="w-full text-left flex items-start gap-2">
        <span className="flex-shrink-0 mt-0.5 w-3.5 h-3.5 rounded border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))]" />
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5">
            <ForeignBadge task={task} />
            <span className={`text-[11px] truncate ${isDone ? "line-through text-[#9aa7bc]" : "text-[#c8d2df]"}`}>
              {task.title}
            </span>
          </span>
          <span className="block text-[9px] text-[#9aa7bc] ml-0.5 mt-0.5">
            {t(`status_${task.status}`)} · {t("foreign_owned_by", { name })}
          </span>
        </span>
      </button>
      {open && <ForeignDetail task={task} initial={initialFull} />}
    </div>
  )
}
