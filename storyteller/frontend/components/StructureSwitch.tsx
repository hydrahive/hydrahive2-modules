// C2 – Schalter je Buch „Autor darf die Gliederung direkt ändern“ (Spec autor-gliederung-c2.md §2b).
// Gespeichert in book.ghost.agent_structure (propose | direct). Leser sehen ihn gesperrt.
import { useTranslation } from "react-i18next"
import { agentStructure, withAgentStructure } from "../restructure"
import type { BookState } from "../useBook"

export function StructureSwitch({ state }: { state: BookState }) {
  const { t } = useTranslation("storyteller")
  const { book, canWrite } = state
  const direct = agentStructure(book.ghost) === "direct"
  return (
    <fieldset className="st-struct-switch space-y-1 text-xs text-[#c8d2df]" disabled={!canWrite}>
      <label className="flex items-center gap-1.5">
        <input type="checkbox" checked={direct} onChange={(e) => state.change((b) => withAgentStructure(b, e.target.checked))} />
        {t("struct_switch")}
      </label>
      <p className="text-[11px] text-[#9aa7bc]">{t("struct_switch_help")}</p>
    </fieldset>
  )
}
