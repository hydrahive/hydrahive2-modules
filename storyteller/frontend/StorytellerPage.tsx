// Einstieg: Projekt wählen → Bücherliste → Arbeitsplatz.
import { lazy, Suspense, useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { BookList } from "./components/BookList"
import { draftStore } from "./draftStore"
import type { Book } from "./model"

const PROJECT_KEY = "storyteller.project"
// Arbeitsplatz (mit Prosa-Editor) erst beim Öffnen eines Buchs laden – hält andere Seiten schlank.
const Workspace = lazy(() => import("./components/Workspace").then((m) => ({ default: m.Workspace })))

export function StorytellerPage() {
  const { t } = useTranslation("storyteller")
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [projectId, setProjectId] = useState("")
  const [open, setOpen] = useState<{ book: Book; sceneId?: string } | null>(null)
  const [tick, setTick] = useState(0)

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

  const close = useCallback(() => { setOpen(null); setTick((n) => n + 1) }, [])

  if (open && projectId) {
    return (
      <Suspense fallback={<div className="p-8 text-sm text-zinc-500">…</div>}>
        <Workspace key={open.book.id} projectId={projectId} initial={open.book} initialSceneId={open.sceneId} onClose={close} />
      </Suspense>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-black tracking-tight text-zinc-100">
            {t("title")}
            <span className="rounded border border-amber-400/40 bg-amber-400/10 px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wider text-amber-300">
              {t("draft_badge")}
            </span>
          </h1>
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
      <p className="rounded-lg border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-xs text-amber-200/80">{t("draft_hint")}</p>
      {projects === null ? null : projects.length === 0 ? (
        <p className="text-sm text-zinc-400">{t("project_none")}</p>
      ) : (
        <BookList key={`${projectId}-${tick}`} projectId={projectId}
          last={draftStore.last(projectId)}
          onOpen={(book, sceneId) => setOpen({ book, sceneId })} />
      )}
    </div>
  )
}
