import { Command, HelpCircle, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { DEMO_JOBS } from "./demoData"
import { WORKSPACES, type Workspace } from "./workspaces"

interface Props {
  workspace: Workspace
  onWorkspace: (w: Workspace) => void
  onCommand: () => void
  onHelp: () => void
}

/** Kopfzeile: Projekt, Arbeitsbereiche als Reiter, laufende Aufträge, Befehlssuche, Hilfe. */
export function StudioHeader({ workspace, onWorkspace, onCommand, onHelp }: Props) {
  const { t } = useTranslation("studio")
  return (
    <header className="flex h-11 shrink-0 items-center gap-3 border-b border-[#2a364b] bg-[#0d1420] px-3">
      <span className="text-sm font-black tracking-tight text-[#e8eef8]">{t("title")}</span>
      <select className="rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-1 text-xs text-[#c3ccdd]" aria-label={t("project")}>
        <option>Nordwind (Beispiel)</option>
      </select>
      <nav className="mx-auto flex items-center gap-0.5" aria-label={t("workspaces")}>
        {WORKSPACES.map((w) => (
          <button key={w} type="button" data-studio-workspace={w} aria-pressed={w === workspace}
            onClick={() => onWorkspace(w)}
            className={`rounded-[4px] px-3 py-1.5 text-xs font-bold transition ${w === workspace
              ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#8d9ab0] hover:bg-[#111827] hover:text-[#e8eef8]"}`}>
            {t(`ws.${w}`)}
          </button>
        ))}
      </nav>
      <button type="button" data-studio-jobs className="flex items-center gap-1.5 rounded-[4px] px-2 py-1 text-[11px] text-[#8d9ab0] hover:bg-[#111827]"
        title={DEMO_JOBS.map((j) => `${j.label} · ${j.percent}%`).join("\n")}>
        <Loader2 size={12} className="animate-spin text-[#ffb86b]" /> {t("jobs", { count: DEMO_JOBS.length })}
      </button>
      <button type="button" onClick={onCommand} data-studio-action="command"
        className="flex items-center gap-1.5 rounded-[4px] border border-[#2a364b] px-2 py-1 text-[11px] text-[#8d9ab0] hover:text-[#e8eef8]">
        <Command size={12} /> {t("command_hint")}
      </button>
      <button type="button" onClick={onHelp} aria-label={t("help_title")} data-studio-action="help"
        className="rounded-[4px] p-1 text-[#8d9ab0] hover:text-[#e8eef8]">
        <HelpCircle size={15} />
      </button>
    </header>
  )
}
