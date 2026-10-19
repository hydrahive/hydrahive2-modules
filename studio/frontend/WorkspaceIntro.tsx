import { ArrowRight, Info, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { nextWorkspace, stepOf } from "./guideLogic"
import { WORKSPACES, type Workspace } from "./workspaces"

/** Unter der Kopfzeile (C3): „Schritt X von 6 – …“, worum es geht, und weiter zum nächsten Reiter. Einklappbar. */
export function WorkspaceIntro({ workspace, open, onToggle, onGo }: { workspace: Workspace; open: boolean; onToggle: () => void
  onGo?: (w: Workspace) => void }) {
  const { t } = useTranslation("studio")
  const next = nextWorkspace(workspace)
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
      <p className="min-w-0 flex-1">
        <b className="mr-1.5 text-[#e8eef8]">{t("intro_step", { n: stepOf(workspace), total: WORKSPACES.length, name: t(`ws.${workspace}`) })}</b>
        {t(`intro.${workspace}`)}
      </p>
      {onGo && next && (
        <button type="button" onClick={() => onGo(next)} data-intro-next={next}
          className="flex shrink-0 items-center gap-1 rounded-[4px] border border-[#46617f] px-2 py-0.5 font-bold text-[#69d7ff] hover:bg-[#1c2940]">
          {t("intro_next", { name: t(`ws.${next}`) })} <ArrowRight size={11} />
        </button>
      )}
      <button type="button" onClick={onToggle} aria-label={t("intro_hide")} title={t("intro_hide")} className="rounded p-0.5 text-[#68758a] hover:text-[#e8eef8]">
        <X size={12} />
      </button>
    </div>
  )
}
