import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { tonstudioApi } from "./api"
import { errText, registerTonstudioErrors } from "./errors"
import { GenerateDialog } from "./GenerateDialog"
import { Library } from "./Library"
import { SongList } from "./SongList"
import type { LibraryItem, SongSummary } from "./types"

/** Tonstudio M1: Projektwahl, Songs, Bibliothek, Clips erzeugen (SPEC.md). Zeitachse/Mixdown folgen in M2. */
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

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <header className="flex flex-wrap items-center gap-3">
        <h1 className="text-lg font-semibold text-slate-100">🎚️ {t("title")}</h1>
        <select
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          aria-label={t("select_project")}
          className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200"
        >
          {projects.length === 0 && <option value="">{t("no_projects")}</option>}
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <span className="text-xs text-slate-500">{t("m1_hint")}</span>
      </header>
      {error && <p className="text-sm text-red-400">{error}</p>}
      {projectId && (
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
          <div className="flex flex-col gap-4">
            <SongList projectId={projectId} songs={songs} trash={trash} onChanged={() => reload(projectId)} />
            <GenerateDialog projectId={projectId} onDone={() => reload(projectId)} />
          </div>
          <Library projectId={projectId} items={library} onChanged={() => reload(projectId)} />
        </div>
      )}
    </div>
  )
}
