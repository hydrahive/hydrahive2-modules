import { Command, HelpCircle, Loader2, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { StudioProject } from "./api"
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
  running?: number
  batch?: React.ReactNode
  progress?: React.ReactNode
}

/** Studio-Leiste: Projekt, Arbeitsbereiche als Reiter, laufende Aufträge, Befehlssuche, Hilfe. */
export function StudioHeader({ projects, projectId, onProject, onReload, workspace, onWorkspace, onCommand, onHelp, running = 0, batch, progress }: Props) {
  const { t } = useTranslation("studio")
  return (
    // Umbruch statt Überstand: bei schmalen Fenstern rutscht der Rest in eine zweite Zeile, nichts ragt hinaus
    <header className="flex min-h-11 shrink-0 flex-wrap items-center gap-x-3 gap-y-1 border-b border-[#2a364b] bg-[#0d1420] px-3 py-1" data-studio-header>
      <select value={projectId} onChange={(e) => onProject(e.target.value)} data-studio-project aria-label={t("project")}
        className="max-w-[16rem] rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-1 text-xs text-[#c3ccdd]">
        {!projects.length && <option value="">{t("no_projects")}</option>}
        {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      </select>
      <button type="button" onClick={onReload} title={t("reload")} aria-label={t("reload")} className="rounded-[4px] p-1 text-[#8d9ab0] hover:text-[#e8eef8]">
        <RefreshCw size={13} />
      </button>
      <nav className="mx-auto flex items-center gap-0.5" aria-label={t("workspaces")}>
        {/* Reiter in der Reihenfolge der Arbeit; die Nummern machen sie als Schritte erkennbar */}
        {WORKSPACES.map((w) => (
          <button key={w} type="button" data-studio-workspace={w} aria-pressed={w === workspace}
            onClick={() => onWorkspace(w)}
            className={`rounded-[4px] px-2 py-1.5 text-xs font-bold transition 2xl:px-3 ${w === workspace
              ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#8d9ab0] hover:bg-[#111827] hover:text-[#e8eef8]"}`}>
            <span className="mr-1 text-[10px] text-[#68758a]">{WORKSPACES.indexOf(w) + 1}</span>{t(`ws.${w}`)}
          </button>
        ))}
      </nav>
      {progress}
      {batch ?? (running > 0 && (
        <span data-studio-jobs className="flex items-center gap-1.5 rounded-[4px] px-2 py-1 text-[11px] text-[#8d9ab0]">
          <Loader2 size={12} className="animate-spin text-[#ffb86b]" /> {t("jobs", { count: running })}
        </span>
      ))}
      <button type="button" onClick={onCommand} data-studio-action="command"
        className="flex items-center gap-1.5 rounded-[4px] border border-[#2a364b] px-2 py-1 text-[11px] text-[#8d9ab0] hover:text-[#e8eef8]">
        <Command size={12} /> {t("command_hint")}
      </button>
      <button type="button" onClick={onHelp} data-studio-action="help"
        className="flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 text-[11px] font-bold text-[#c3ccdd] hover:text-[#e8eef8]">
        <HelpCircle size={13} /> {t("howto_title")}
      </button>
    </header>
  )
}
