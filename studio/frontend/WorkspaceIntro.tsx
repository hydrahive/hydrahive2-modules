import { Info, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Workspace } from "./workspaces"

/** Eine Zeile unter der Kopfzeile: worum es in diesem Reiter geht. Einklappbar, der Zustand wird gemerkt. */
export function WorkspaceIntro({ workspace, open, onToggle }: { workspace: Workspace; open: boolean; onToggle: () => void }) {
  const { t } = useTranslation("studio")
  if (!open) {
    return (
      <button type="button" onClick={onToggle} aria-label={t("intro_show")} title={t("intro_show")} data-studio-intro="closed"
        className="absolute right-2 top-[2.85rem] z-10 rounded-full p-1 text-[#68758a] hover:bg-[#111827] hover:text-[#69d7ff]">
        <Info size={13} />
      </button>
    )
  }
  return (
    <div className="flex shrink-0 items-start gap-2 border-b border-[#2a364b] bg-[#0f1726] px-3 py-1.5 text-[11px] leading-relaxed text-[#c3ccdd]" data-studio-intro={workspace}>
      <Info size={13} className="mt-0.5 shrink-0 text-[#69d7ff]" />
      <p className="min-w-0 flex-1">{t(`intro.${workspace}`)}</p>
      <button type="button" onClick={onToggle} aria-label={t("intro_hide")} title={t("intro_hide")} className="rounded p-0.5 text-[#68758a] hover:text-[#e8eef8]">
        <X size={12} />
      </button>
    </div>
  )
}
