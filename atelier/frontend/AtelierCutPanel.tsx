import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import type { VideoMeta } from "../videoeditor/types"
import { videoeditorApi } from "../videoeditor/api"
import { EditorView } from "../videoeditor/EditorView"
import { BrowseDialog } from "../videoeditor/BrowseDialog"

interface Props {
  projectId: string
}

/** Atelier-Schnitt-Tab: bettet den bestehenden Videoeditor ohne eigene
 *  Projektauswahl ein. Der Videoeditor browsed den gesamten Projekt-Workspace,
 *  daher tauchen Atelier-Clips (atelier/videos/*.mp4) automatisch als Quellen auf. */
export function AtelierCutPanel({ projectId }: Props) {
  const { t } = useTranslation("atelier")
  const [files, setFiles] = useState<VideoMeta[]>([])
  const [openFile, setOpenFile] = useState<VideoMeta | null>(null)
  const [showBrowse, setShowBrowse] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const reload = useCallback(async () => {
    if (!projectId) return
    try { setFiles(await videoeditorApi.listFiles(projectId)) } catch { setFiles([]) }
  }, [projectId])

  useEffect(() => { reload() }, [reload])

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
        if (job.status === "failed") throw new Error(job.error || t("cut_upload_failed"))
      }
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setUploading(false)
    }
  }

  if (openFile) {
    return <EditorView projectId={projectId} meta={openFile} onBack={() => { setOpenFile(null); reload() }} />
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">✂️ {t("tab_cut")}</h3>
          <p className="text-xs text-slate-500">{t("cut_library_hint")}</p>
        </div>
        <span className="flex-1" />
        <button
          onClick={() => setShowBrowse(true)}
          className="rounded border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs text-sky-300 hover:bg-sky-500/20"
        >
          {t("cut_add_from_project")}
        </button>
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="rounded border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-xs text-violet-200 hover:bg-violet-500/20 disabled:opacity-40"
        >
          {uploading ? t("uploading") : t("cut_upload")}
        </button>
        <input ref={fileRef} type="file" accept="video/*" className="hidden" onChange={onFile} />
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      {files.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-8 text-center text-sm text-slate-500">
          {t("cut_empty")}
        </div>
      ) : (
        <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(240px,1fr))]">
          {files.map((f) => (
            <button
              key={f.file_id}
              onClick={() => setOpenFile(f)}
              className="overflow-hidden rounded-lg border border-slate-700 bg-slate-900/40 text-left transition-colors hover:border-violet-500/50"
            >
              <div className="grid aspect-video place-items-center bg-black/40 text-xs text-slate-500">
                {f.width}×{f.height}
              </div>
              <div className="space-y-1 p-2">
                <p className="truncate text-xs text-slate-200">{f.filename}</p>
                <p className="truncate text-[10px] text-slate-500">{f.source_rel}</p>
                <p className="text-[10px] text-slate-500">{f.duration?.toFixed(1)}s · {f.edl?.timeline?.length ?? 0} {t("cut_clips")}</p>
              </div>
            </button>
          ))}
        </div>
      )}

      {showBrowse && (
        <BrowseDialog projectId={projectId} onClose={() => setShowBrowse(false)} onImported={() => reload()} />
      )}
    </div>
  )
}
