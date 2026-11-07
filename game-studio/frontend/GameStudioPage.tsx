import { AlertTriangle, LoaderCircle } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { gameStudioApi } from "./api"
import { GuidedFlow } from "./GuidedFlow"
import { LandingPage } from "./LandingPage"
import type { ProjectCreate, ProjectPatch, EntryKind, GameProject, GameStudioOverview } from "./types"

export function GameStudioPage() {
  const { t } = useTranslation("gameStudio")
  const [overview, setOverview] = useState<GameStudioOverview | null>(null)
  const [kind, setKind] = useState<EntryKind | null>(null)
  const [project, setProject] = useState<GameProject | null>(null)
  const [error, setError] = useState(false)

  const reload = () => {
    setError(false)
    gameStudioApi.overview().then(setOverview).catch(() => setError(true))
  }

  useEffect(() => { reload() }, [])

  const start = (entryKind: EntryKind) => {
    setKind(entryKind)
    setProject(null)
  }

  const open = (selected: GameProject) => {
    setKind(selected.entry_kind)
    setProject(selected)
  }

  const create = async (body: ProjectCreate) => {
    const created = await gameStudioApi.createProject(body)
    setProject(created)
    setOverview((current) => current ? { ...current, projects: [created, ...current.projects] } : current)
    return created
  }

  const update = async (currentProject: GameProject, patch: ProjectPatch) => {
    const updated = await gameStudioApi.updateProject(currentProject.project_id, patch)
    setProject(updated)
    setOverview((current) => current ? {
      ...current,
      projects: current.projects.map((item) => item.project_id === updated.project_id ? updated : item),
    } : current)
    return updated
  }

  const reloadProject = async (currentProject: GameProject) => {
    const updated = await gameStudioApi.project(currentProject.project_id)
    setProject(updated)
    setOverview((current) => current ? {
      ...current,
      projects: current.projects.map((item) => item.project_id === updated.project_id ? updated : item),
    } : current)
    return updated
  }

  const generateUnrealProject = async (currentProject: GameProject) => {
    const updated = await gameStudioApi.generateUnrealProject(currentProject.project_id, currentProject.revision)
    setProject(updated)
    setOverview((current) => current ? {
      ...current,
      projects: current.projects.map((item) => item.project_id === updated.project_id ? updated : item),
    } : current)
    return updated
  }

  const back = () => {
    setKind(null)
    setProject(null)
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

  if (kind) {
    return <GuidedFlow kind={kind} project={project} onBack={back} onCreate={create} onUpdate={update} onGenerateUnreal={generateUnrealProject} onReloadProject={reloadProject} />
  }

  return <LandingPage projects={overview.projects} sharing={overview.sharing} onStart={start} onOpen={open} />
}
