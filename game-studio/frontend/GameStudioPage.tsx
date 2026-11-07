import { AlertTriangle, LoaderCircle } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { gameStudioApi } from "./api"
import { setupComplete } from "./flow"
import { GuidedFlow } from "./GuidedFlow"
import { LandingPage } from "./LandingPage"
import { ProjectWorkspace } from "./ProjectWorkspace"
import type { ProjectCreate, ProjectPatch, EntryKind, GameProject, GameStudioOverview } from "./types"

type View = { mode: "landing" } | { mode: "setup"; kind: EntryKind } | { mode: "workspace" }

export function GameStudioPage() {
  const { t } = useTranslation("gameStudio")
  const [overview, setOverview] = useState<GameStudioOverview | null>(null)
  const [view, setView] = useState<View>({ mode: "landing" })
  const [project, setProject] = useState<GameProject | null>(null)
  const [error, setError] = useState(false)

  const reload = () => {
    setError(false)
    gameStudioApi.overview().then(setOverview).catch(() => setError(true))
  }

  useEffect(() => { reload() }, [])

  const replaceProject = (updated: GameProject) => {
    setProject(updated)
    setOverview((current) => current ? {
      ...current,
      projects: current.projects.map((item) => item.project_id === updated.project_id ? updated : item),
    } : current)
    return updated
  }

  const start = (entryKind: EntryKind) => {
    setProject(null)
    setView({ mode: "setup", kind: entryKind })
  }

  const open = (selected: GameProject) => {
    setProject(selected)
    setView(setupComplete(selected) ? { mode: "workspace" } : { mode: "setup", kind: selected.entry_kind })
  }

  const create = async (body: ProjectCreate) => {
    const created = await gameStudioApi.createProject(body)
    setProject(created)
    setOverview((current) => current ? { ...current, projects: [created, ...current.projects] } : current)
    return created
  }

  const update = async (currentProject: GameProject, patch: ProjectPatch) =>
    replaceProject(await gameStudioApi.updateProject(currentProject.project_id, patch))

  const generateUnrealProject = async (currentProject: GameProject) =>
    replaceProject(await gameStudioApi.generateUnrealProject(currentProject.project_id, currentProject.revision))

  const back = () => {
    setView({ mode: "landing" })
    setProject(null)
    const url = new URL(window.location.href)
    url.searchParams.delete("tab")
    window.history.replaceState(window.history.state, "", url)
    reload()
  }

  if (error) {
    return (
      <main className="mx-auto flex min-h-[60vh] max-w-xl items-center justify-center px-5 text-center">
        <div><AlertTriangle className="mx-auto text-amber-300" aria-hidden="true" /><h1 className="mt-3 text-lg font-semibold text-[#e8eef8]">{t("error.title")}</h1><p className="mt-1 text-sm text-[#9aa7bc]">{t("error.text")}</p><button type="button" onClick={reload} className="mt-4 rounded-lg bg-[#69d7ff] px-4 py-2 text-sm font-semibold text-[#0d1420]">{t("error.retry")}</button></div>
      </main>
    )
  }

  if (!overview) {
    return <div className="flex min-h-[60vh] items-center justify-center"><LoaderCircle className="animate-spin text-[#69d7ff]" aria-label={t("loading")} /></div>
  }

  if (view.mode === "workspace" && project) {
    return <ProjectWorkspace project={project} onBack={back} onSetup={() => setView({ mode: "setup", kind: project.entry_kind })} />
  }

  if (view.mode === "setup") {
    return <GuidedFlow kind={view.kind} project={project} onBack={back} onCreate={create} onUpdate={update} onGenerateUnreal={generateUnrealProject}
      onOpenWorkspace={project && setupComplete(project) ? () => setView({ mode: "workspace" }) : undefined} />
  }

  return <LandingPage projects={overview.projects} sharing={overview.sharing} onStart={start} onOpen={open} />
}
