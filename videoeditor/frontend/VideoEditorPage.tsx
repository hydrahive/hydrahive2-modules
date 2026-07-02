import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "@/features/projects/api"
import type { Project } from "@/features/projects/types"
import type { VideoMeta } from "./types"
import { videoeditorApi } from "./api"
import { EditorView } from "./EditorView"
import { BrowseDialog } from "./BrowseDialog"

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

  if (projects.length === 0) {
    return <div className="p-6 text-sm text-zinc-400">{t("no_projects")}</div>
  }

  if (openFile) {
    return (
      <div className="p-4">
        <EditorView projectId={projectId} meta={openFile} onBack={() => { setOpenFile(null); reload(projectId) }} />
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-lg font-semibold text-zinc-100">{t("title")}</h1>
        <select value={projectId} onChange={(e) => setProjectId(e.target.value)}
          className="px-2 py-1 text-sm rounded bg-black/30 border border-white/10 text-zinc-200">
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <span className="flex-1" />
        <button onClick={() => setShowBrowse(true)}
          className="px-3 py-1.5 text-xs rounded bg-sky-500/15 border border-sky-500/30 text-sky-200">
          {t("add_from_project")}
        </button>
        <button onClick={() => fileRef.current?.click()} disabled={uploading}
          className="px-3 py-1.5 text-xs rounded bg-violet-500/15 border border-violet-500/30 text-violet-200 disabled:opacity-40">
          {uploading ? t("uploading") : t("upload")}
        </button>
        <input ref={fileRef} type="file" accept="video/*" className="hidden" onChange={onFile} />
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {files.length === 0 ? (
        <p className="text-sm text-zinc-500">{t("empty")}</p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {files.map((f) => (
            <button key={f.file_id} onClick={() => setOpenFile(f)}
              className="text-left rounded-lg border border-white/10 overflow-hidden hover:border-violet-500/40 transition-colors bg-black/20">
              <div className="aspect-video bg-black/40 flex items-center justify-center text-zinc-600 text-xs">
                {f.width}×{f.height}
              </div>
              <div className="p-2">
                <p className="text-xs text-zinc-200 truncate">{f.filename}</p>
                <p className="text-[10px] text-zinc-500 truncate">{f.source_rel}</p>
                <p className="text-[10px] text-zinc-500">{f.duration?.toFixed(1)}s · {f.edl?.timeline?.length ?? 0} {t("clips")}</p>
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
