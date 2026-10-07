// Einstieg: Projekt wählen → Bücherliste → Arbeitsplatz. Bücher liegen im Projektordner (Spec 1b).
import { lazy, Suspense, useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { storyApi } from "./api"
import { BookList } from "./components/BookList"
import type { Book } from "./model"
import type { InfoProposal } from "./infoProposal"
import { openedFromServer, type ProposalMark, type Versions } from "./serverBook"

const PROJECT_KEY = "storyteller.project"
// Arbeitsplatz (mit Prosa-Editor) erst beim Öffnen eines Buchs laden – hält andere Seiten schlank.
const Workspace = lazy(() => import("./components/Workspace").then((m) => ({ default: m.Workspace })))

interface Opened { book: Book; versions: Versions; sceneId?: string; canWrite: boolean; proposals: Record<string, ProposalMark>; infoProposals: Record<string, InfoProposal> }

export function StorytellerPage() {
  const { t } = useTranslation("storyteller")
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [projectId, setProjectId] = useState("")
  const [open, setOpen] = useState<Opened | null>(null)
  const [opening, setOpening] = useState(false)
  const [error, setError] = useState("")
  const [tick, setTick] = useState(0)
  const project = projects?.find((p) => p.id === projectId)

  useEffect(() => {
    projectsApi.list().then((ps) => {
      setProjects(ps)
      const saved = localStorage.getItem(PROJECT_KEY)
      setProjectId(ps.some((p) => p.id === saved) ? (saved as string) : (ps[0]?.id ?? ""))
    }).catch(() => setProjects([]))
  }, [])

  const pickProject = (id: string) => {
    setProjectId(id)
    localStorage.setItem(PROJECT_KEY, id)
  }

  const openBook = useCallback(async (bookId: string, sceneId?: string) => {
    setOpening(true)
    setError("")
    try {
      setOpen({ ...openedFromServer(await storyApi.openBook(projectId, bookId)), sceneId })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setOpening(false) }
  }, [projectId])

  const close = useCallback(() => { setOpen(null); setTick((n) => n + 1) }, [])

  if (open && project) {
    return (
      <Suspense fallback={<div className="p-8 text-sm text-zinc-500">…</div>}>
        <Workspace key={open.book.id} projectId={projectId} projectName={project.name} initial={open.book}
          versions={open.versions} initialSceneId={open.sceneId} canWrite={open.canWrite} proposals={open.proposals} infoProposals={open.infoProposals}
          onClose={close} />
      </Suspense>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-zinc-100">{t("title")}</h1>
          <p className="mt-1 text-sm text-zinc-400">{t("subtitle")}</p>
        </div>
        {projects && projects.length > 0 && (
          <label className="flex items-center gap-2 text-sm text-zinc-400">
            {t("project")}
            <select value={projectId} onChange={(e) => pickProject(e.target.value)}
              className="rounded-lg border border-white/10 bg-zinc-900 px-3 py-1.5 text-zinc-100">
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
        )}
      </header>
      {project && <p className="text-xs text-zinc-500">{t("storage_hint", { name: project.name })}</p>}
      {error && <p className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200" role="alert">{error}</p>}
      {opening && <p className="text-sm text-zinc-500">{t("opening")}</p>}
      {projects === null ? null : projects.length === 0 ? (
        <p className="text-sm text-zinc-400">{t("project_none")}</p>
      ) : (
        <BookList key={`${projectId}-${tick}`} projectId={projectId} onOpen={(id, sceneId) => { void openBook(id, sceneId) }} />
      )}
    </div>
  )
}
