import { useTranslation } from "react-i18next"
import type { Plan, Selection } from "./planApi"
import { PlanPreview } from "./PlanPreview"
import { StartCard } from "./StartCard"

interface Props {
  plan: Plan | null
  selection: Selection | null
  atelier: boolean
  books: number
  busy: boolean
  onStart: () => void
  onImport: () => void
  onIdea: () => void
  onBook: () => void
  onHead: () => void
}

/** Mitte in „Planen“/„Erzeugen“: ohne Szenen das Startfeld, ohne Auswahl ein Hinweis mit Knopf, sonst die Vorschau. */
export function PlanCenter({ plan, selection, atelier, books, busy, onStart, onImport, onIdea, onBook, onHead }: Props) {
  const { t } = useTranslation("studio")
  let body: React.ReactNode
  if (plan && !plan.scenes.length) body = <StartCard atelier={atelier} books={books} busy={busy} onStart={onStart} onImport={onImport} onIdea={onIdea} onBook={onBook} />
  else if (plan && !selection) {
    body = (
      <div className="max-w-sm space-y-3 text-center text-xs leading-relaxed text-[#8d9ab0]" data-plan-pick>
        <p>{t("plan_pick_scene")}</p>
        <button type="button" onClick={onHead} className="rounded-[4px] border border-[#46617f] px-3 py-1.5 font-bold text-[#69d7ff] hover:bg-[#1c2940]">
          {t("plan_edit_head")}
        </button>
      </div>
    )
  } else body = <PlanPreview plan={plan} selection={selection} />
  return <div className="flex h-full min-h-0 items-center justify-center overflow-y-auto p-3" data-studio-panel="preview">{body}</div>
}
