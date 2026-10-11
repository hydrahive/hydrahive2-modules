import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CockpitPanel } from "@/features/cockpit/CockpitPanel"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { tonstudioApi } from "./api"
import { errText, registerTonstudioErrors } from "./errors"
import { GenerateDialog } from "./GenerateDialog"
import { Library } from "./Library"
import { SongList } from "./SongList"
import type { LibraryItem, SongSummary } from "./types"

/** Tonstudio M1 als Cockpit-Seite (nav cockpit:true → der Kern rendert ohne Theme-Rahmen, das Gerüst kommt von hier:
 *  CockpitShell + CockpitTopbar + Raster links/Mitte/rechts wie Projekt-Cockpit). Zeitachse/Mixdown folgen in M2. */
export function TonstudioPage() {
  const { t } = useTranslation("tonstudio")
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState("")
  const [songs, setSongs] = useState<SongSummary[]>([])
  const [trash, setTrash] = useState<SongSummary[]>([])
  const [library, setLibrary] = useState<LibraryItem[]>([])
  const [error, setError] = useState("")

  useEffect(() => {
    registerTonstudioErrors()
    projectsApi.list().then((ps) => {
      setProjects(ps)
      setProjectId((cur) => cur || ps[0]?.id || "")
    }).catch((e) => setError(errText(e)))
  }, [])

  const reload = useCallback(async (pid: string) => {
    if (!pid) return
    setError("")
    try {
      const [s, tr, lib] = await Promise.all([tonstudioApi.songs(pid), tonstudioApi.trash(pid), tonstudioApi.library(pid)])
      setSongs(s)
      setTrash(tr)
      setLibrary(lib)
    } catch (e) {
      setError(errText(e))
    }
  }, [])

  useEffect(() => {
    reload(projectId)
  }, [projectId, reload])

  const project = projects.find((p) => p.id === projectId)
  const changed = () => reload(projectId)

  return (
    <CockpitShell title={t("title")} hideHeader className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]">
      <CockpitTopbar active="/tonstudio" context={project ? `${t("title")} · ${project.name}` : t("title")} />
      {error && (
        <div className="mx-[10px] mt-[10px] shrink-0 rounded-[4px] border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error}
        </div>
      )}
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-y-auto p-[10px] xl:grid-cols-[280px_minmax(420px,1fr)_380px] xl:overflow-hidden">
        <aside className="min-h-0 space-y-[10px] overflow-y-auto pr-1">
          <CockpitPanel eyebrow={t("project")}>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              aria-label={t("select_project")}
              className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]"
            >
              {projects.length === 0 && <option value="">{t("no_projects")}</option>}
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <p className="mt-2 text-xs text-[#8d9ab0]">{t("m1_hint")}</p>
          </CockpitPanel>
          {projectId && (
            <CockpitPanel eyebrow={t("songs")}>
              <SongList projectId={projectId} songs={songs} trash={trash} onChanged={changed} />
            </CockpitPanel>
          )}
        </aside>

        <main className="min-h-0 overflow-y-auto">
          {projectId && (
            <CockpitPanel eyebrow={t("library")} className="min-h-full">
              <Library projectId={projectId} items={library} onChanged={changed} />
            </CockpitPanel>
          )}
        </main>

        <aside className="min-h-0 overflow-y-auto pl-1">
          {projectId && (
            <CockpitPanel eyebrow={t("generate")}>
              <GenerateDialog projectId={projectId} onDone={changed} />
            </CockpitPanel>
          )}
        </aside>
      </div>
    </CockpitShell>
  )
}
