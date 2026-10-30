import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import { HelpButton } from "@/i18n/HelpButton"
import type { VideoMeta } from "./types"
import { videoeditorApi } from "./api"
import { EditorView } from "./EditorView"
import { BrowseDialog } from "./BrowseDialog"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import leerBild from "./assets/leer.webp"

export function VideoEditorPage() {
  const { t } = useTranslation("videoeditor")
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState("")
  const [files, setFiles] = useState<VideoMeta[]>([])
  const [openFile, setOpenFile] = useState<VideoMeta | null>(null)
  const [showBrowse, setShowBrowse] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    projectsApi.list().then((ps) => {
      setProjects(ps)
      if (ps.length && !projectId) setProjectId(ps[0].id)
    }).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const reload = useCallback(async (pid: string) => {
    if (!pid) return
    try { setFiles(await videoeditorApi.listFiles(pid)) } catch { setFiles([]) }
  }, [])

  useEffect(() => { if (projectId) reload(projectId) }, [projectId, reload])

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (!f || !projectId) return
    e.target.value = ""
    setUploading(true); setError(null)
    try {
      const { job_id } = await videoeditorApi.upload(projectId, f)
      for (let i = 0; i < 300; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const job = await videoeditorApi.getJob(projectId, job_id)
        if (job.status === "done") break
        if (job.status === "failed") throw new Error(job.error || t("upload_failed"))
      }
      await reload(projectId)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setUploading(false)
    }
  }

  const shell = (children: ReactNode) => (
    <CockpitShell
      title={t("title")}
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[rgb(var(--hh-s-grund,8_11_17))]"
      hideHeader
    >
      <CockpitTopbar active="/videoeditor" context={t("title")} />
      <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
    </CockpitShell>
  )

  if (projects.length === 0) {
    return shell(<div className="text-sm text-[#9aa7bc]">{t("no_projects")}</div>)
  }

  if (openFile) {
    return shell(<EditorView projectId={projectId} meta={openFile} onBack={() => { setOpenFile(null); reload(projectId) }} />)
  }

  return shell(
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-lg font-semibold text-[#e8eef8]">{t("title")}</h1>
        <HelpButton topic="videoeditor" />
        <select value={projectId} onChange={(e) => setProjectId(e.target.value)}
          className="px-2 py-1 text-sm rounded bg-black/30 border border-[rgb(var(--hh-s-rand,42_54_75))] text-[#e8eef8]">
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <span className="flex-1" />
        <button onClick={() => setShowBrowse(true)}
          className="px-3 py-1.5 text-xs rounded bg-sky-500/15 border border-sky-500/30 text-sky-200">
          {t("add_from_project")}
        </button>
        <button onClick={() => fileRef.current?.click()} disabled={uploading}
          className="px-3 py-1.5 text-xs rounded bg-[#69d7ff]/15 border border-[#69d7ff]/30 text-[#69d7ff] disabled:opacity-40">
          {uploading ? t("uploading") : t("upload")}
        </button>
        <input ref={fileRef} type="file" accept="video/*" className="hidden" onChange={onFile} />
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {files.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-4 text-center"><img src={leerBild} alt="" loading="lazy" draggable={false} className="mx-auto h-20 w-20 select-none object-contain" /><p className="text-sm text-[#9aa7bc]">{t("empty")}</p></div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {files.map((f) => (
            <button key={f.file_id} onClick={() => setOpenFile(f)}
              className="text-left rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] overflow-hidden hover:border-[#69d7ff]/40 transition-colors bg-black/20">
              <div className="aspect-video bg-black/40 flex items-center justify-center text-[#9aa7bc] text-xs">
                {f.width}×{f.height}
              </div>
              <div className="p-2">
                <p className="text-xs text-[#e8eef8] truncate">{f.filename}</p>
                <p className="text-[10px] text-[#9aa7bc] truncate">{f.source_rel}</p>
                <p className="text-[10px] text-[#9aa7bc]">{f.duration?.toFixed(1)}s · {f.edl?.timeline?.length ?? 0} {t("clips")}</p>
              </div>
            </button>
          ))}
        </div>
      )}

      {showBrowse && (
        <BrowseDialog projectId={projectId} onClose={() => setShowBrowse(false)}
          onImported={() => reload(projectId)} />
      )}
    </div>
  )
}
