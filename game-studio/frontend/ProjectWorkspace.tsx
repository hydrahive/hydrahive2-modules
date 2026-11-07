// Projekt-Arbeitsfläche: Tabs aus tabs/registry.ts, Agent-Chat rechts andockbar.
import { ArrowLeft, MessagesSquare, Settings2 } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { AgentDock } from "./components/AgentDock"
import { DOCK_KEY, readDock, type DockState } from "./dock"
import { WORKSPACE_TABS, tabById } from "./tabs/registry"
import type { GameProject } from "./types"

interface Props { project: GameProject; onBack: () => void; onSetup: () => void }

function readTab(): string | null {
  return new URLSearchParams(window.location.search).get("tab")
}

function writeTab(id: string) {
  const url = new URL(window.location.href)
  url.searchParams.set("tab", id)
  window.history.replaceState(window.history.state, "", url)
}

export function ProjectWorkspace({ project, onBack, onSetup }: Props) {
  const { t } = useTranslation("gameStudio")
  const [tabId, setTabId] = useState(() => tabById(readTab()).id)
  const [dock, setDockState] = useState<DockState>(() => readDock(localStorage.getItem(DOCK_KEY), window.innerWidth))
  const active = tabById(tabId)
  const ActiveTab = active.component

  const setDock = (next: DockState) => {
    setDockState(next)
    try { localStorage.setItem(DOCK_KEY, JSON.stringify(next)) } catch { /* privater Modus: egal */ }
  }
  const selectTab = (id: string) => { setTabId(id); writeTab(id) }
  const openAgent = () => setDock({ ...dock, open: true })

  return (
    <div className="flex h-full min-h-[calc(100dvh-64px)]">
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-3 border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-4 py-3 sm:px-6">
          <button type="button" onClick={onBack} title={t("flow.back")} className="rounded p-1 text-[#9aa7bc] hover:text-[#e8eef8]"><ArrowLeft size={18} aria-hidden="true" /></button>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-lg font-semibold text-[#e8eef8]">{project.title}</h1>
            <p className="text-[11px] text-[#9aa7bc]">{t(`engine.${project.engine}`)}</p>
          </div>
          <button type="button" onClick={onSetup} className="inline-flex items-center gap-1.5 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1.5 text-xs text-[#c8d2df] hover:text-[#e8eef8]">
            <Settings2 size={14} aria-hidden="true" />{t("workspace.setup")}
          </button>
          {!dock.open && (
            <button type="button" onClick={openAgent} className="inline-flex items-center gap-1.5 rounded-lg bg-[#69d7ff] px-3 py-1.5 text-xs font-semibold text-[#0d1420] hover:bg-[#9ee6ff]">
              <MessagesSquare size={14} aria-hidden="true" />{t("workspace.agent.open")}
            </button>
          )}
        </header>
        <nav role="tablist" aria-label={t("workspace.tablist")} className="flex gap-1 overflow-x-auto border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-4 sm:px-6">
          {WORKSPACE_TABS.map((tab) => {
            const Icon = tab.icon
            const selected = tab.id === active.id
            return (
              <button key={tab.id} type="button" role="tab" aria-selected={selected} onClick={() => selectTab(tab.id)}
                className={`flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm ${selected ? "border-[#69d7ff] text-[#e8eef8]" : "border-transparent text-[#9aa7bc] hover:text-[#e8eef8]"}`}>
                <Icon size={15} aria-hidden="true" />{t(tab.labelKey)}
              </button>
            )
          })}
        </nav>
        <main role="tabpanel" className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
          <ActiveTab project={project} onOpenAgent={openAgent} />
        </main>
      </div>
      {dock.open && (
        <AgentDock projectId={project.project_id} width={dock.width}
          onWidth={(width) => setDock({ ...dock, width })} onClose={() => setDock({ ...dock, open: false })} />
      )}
    </div>
  )
}
