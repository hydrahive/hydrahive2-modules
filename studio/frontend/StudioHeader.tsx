import { Command, HelpCircle, Loader2, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { StudioProject } from "./api"
import { DEMO_JOBS } from "./demoData"
import { WORKSPACES, type Workspace } from "./workspaces"

interface Props {
  projects: StudioProject[]
  projectId: string
  onProject: (id: string) => void
  onReload: () => void
  workspace: Workspace
  onWorkspace: (w: Workspace) => void
  onCommand: () => void
  onHelp: () => void
}

/** Studio-Leiste: Projekt, Arbeitsbereiche als Reiter, laufende Aufträge, Befehlssuche, Hilfe. */
export function StudioHeader({ projects, projectId, onProject, onReload, workspace, onWorkspace, onCommand, onHelp }: Props) {
  const { t } = useTranslation("studio")
  return (
    <header className="flex h-11 shrink-0 items-center gap-3 border-b border-[#2a364b] bg-[#0d1420] px-3">
      <select value={projectId} onChange={(e) => onProject(e.target.value)} data-studio-project aria-label={t("project")}
        className="max-w-[16rem] rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-1 text-xs text-[#c3ccdd]">
        {!projects.length && <option value="">{t("no_projects")}</option>}
        {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select>
      <button type="button" onClick={onReload} title={t("reload")} aria-label={t("reload")} className="rounded-[4px] p-1 text-[#8d9ab0] hover:text-[#e8eef8]">
        <RefreshCw size={13} />
      </button>
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
