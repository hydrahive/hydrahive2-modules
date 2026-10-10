// Einstieg: Projekt wählen → Bücherliste → Arbeitsplatz. Bücher liegen im Projektordner (Spec 1b).
import { lazy, Suspense, useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { storyApi } from "./api"
import { bookProjectApi, errorText, isBookProject } from "./bookProject"
import { BookList } from "./components/BookList"
import { NewBookDialog } from "./components/NewBookDialog"
import type { Book } from "./model"
import type { OutlineProposal } from "./chatApi"
import type { RestructureProposal } from "./restructure"
import type { EntityProposal } from "./entityProposal"
import type { InfoProposal } from "./infoProposal"
import { openedFromServer, type ProposalMark, type Versions } from "./serverBook"

const PROJECT_KEY = "storyteller.project"
// Arbeitsplatz (mit Prosa-Editor) erst beim Öffnen eines Buchs laden – hält andere Seiten schlank.
const Workspace = lazy(() => import("./components/Workspace").then((m) => ({ default: m.Workspace })))

interface Opened { book: Book; versions: Versions; sceneId?: string; canWrite: boolean; proposals: Record<string, ProposalMark>; infoProposals: Record<string, InfoProposal>; entityProposals: EntityProposal[]; outlineProposal: OutlineProposal | null; restructureProposal: RestructureProposal | null; openNotes: Record<string, number> }

export function StorytellerPage() {
  const { t } = useTranslation("storyteller")
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [projectId, setProjectId] = useState("")
  const [open, setOpen] = useState<Opened | null>(null)
  const [opening, setOpening] = useState(false)
  const [error, setError] = useState("")
  const [tick, setTick] = useState(0)
  const [canCreateProject, setCanCreateProject] = useState(false)
  const [firstBook, setFirstBook] = useState(false)
  const project = projects?.find((p) => p.id === projectId)

  const loadProjects = useCallback(async (select?: string) => {
    try {
      const ps = await projectsApi.list()
      setProjects(ps)
      const want = select ?? localStorage.getItem(PROJECT_KEY)
      const id = ps.some((p) => p.id === want) ? (want as string) : (ps[0]?.id ?? "")
      setProjectId(id)
      if (select) localStorage.setItem(PROJECT_KEY, id)
    } catch { setProjects([]) }
  }, [])

  useEffect(() => {
    void Promise.resolve().then(() => loadProjects())
    bookProjectApi.canCreate().then((r) => setCanCreateProject(r.can_create)).catch(() => setCanCreateProject(false))
  }, [loadProjects])

  const pickProject = (id: string) => {
    setProjectId(id)
    localStorage.setItem(PROJECT_KEY, id)
  }

  const openBook = useCallback(async (bookId: string, sceneId?: string, inProject?: string) => {
    setOpening(true)
    setError("")
    try {
      setOpen({ ...openedFromServer(await storyApi.openBook(inProject ?? projectId, bookId)), sceneId })
    } catch (e) {
      setError(errorText(t, e))
    } finally { setOpening(false) }
  }, [projectId, t])

  // T1c: Buch als eigenes Projekt angelegt → Projektliste neu laden, Projekt wählen, Buch öffnen.
  const projectCreated = useCallback(async (pid: string, bookId: string) => {
    await loadProjects(pid)
    await openBook(bookId, undefined, pid)
  }, [loadProjects, openBook])

  const createFirst = async (f: Parameters<typeof bookProjectApi.create>[0]) => {
    setFirstBook(false)
    setOpening(true)
    try {
      const out = await bookProjectApi.create(f)
      await projectCreated(out.project_id, out.book.id)
    } catch (e) { setError(errorText(t, e)) } finally { setOpening(false) }
  }

  const close = useCallback(() => { setOpen(null); setTick((n) => n + 1) }, [])

  if (open && project) {
    return (
      <Suspense fallback={<div className="p-8 text-sm text-zinc-500">…</div>}>
        <Workspace key={open.book.id} projectId={projectId} projectName={project.name} initial={open.book}
          versions={open.versions} initialSceneId={open.sceneId} canWrite={open.canWrite} proposals={open.proposals} infoProposals={open.infoProposals} entityProposals={open.entityProposals} outlineProposal={open.outlineProposal} restructureProposal={open.restructureProposal} openNotes={open.openNotes}
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
        <div className="space-y-3">
          <p className="text-sm text-zinc-400">{t(canCreateProject ? "project_none_can_create" : "project_none")}</p>
          {canCreateProject && (
            <button onClick={() => setFirstBook(true)} className="rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-violet-500">
              {t("new_book")}
            </button>
          )}
          {firstBook && <NewBookDialog canCreateProject onCancel={() => setFirstBook(false)} onCreate={(f) => { void createFirst(f) }} />}
        </div>
      ) : (
        <BookList key={`${projectId}-${tick}`} projectId={projectId} projectName={project?.name ?? ""} canCreateProject={canCreateProject}
          bookProject={project ? isBookProject(project as { metadata?: Record<string, unknown> }) : false}
          onOpen={(id, sceneId) => { void openBook(id, sceneId) }}
          onProjectCreated={(pid, bid) => { void projectCreated(pid, bid) }} />
      )}
    </div>
  )
}
