import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import type { BrowseEntry } from "./types"
import { videoeditorApi } from "./api"

interface Props {
  projectId: string
  onClose: () => void
  onImported: () => void
}

/** Dialog: Videos, die schon im Projekt-Workspace liegen (z.B. Atelier-
 *  Videos), zum Schnitt hinzufügen — OHNE Kopie, nur Proxy/Keyframes werden
 *  erzeugt. Kein Silo: alles was zum Projekt gehört, bleibt im Workspace. */
export function BrowseDialog({ projectId, onClose, onImported }: Props) {
  const { t } = useTranslation("videoeditor")
  const [entries, setEntries] = useState<BrowseEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    videoeditorApi.browse(projectId)
      .then(setEntries)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [projectId])

  async function doImport(entry: BrowseEntry) {
    setImporting(entry.source_rel); setError(null)
    try {
      const { job_id } = await videoeditorApi.importVideo(projectId, entry.source_rel)
      for (let i = 0; i < 300; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const job = await videoeditorApi.getJob(projectId, job_id)
        if (job.status === "done") break
        if (job.status === "failed") throw new Error(job.error || t("import_failed"))
      }
      onImported()
      setEntries((es) => es.map((e) => e.source_rel === entry.source_rel ? { ...e, imported: true } : e))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setImporting(null)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="w-full max-w-lg max-h-[80vh] flex flex-col rounded-lg border border-white/10 bg-zinc-900">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <p className="text-sm font-semibold text-zinc-100">{t("browse_title")}</p>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200">✕</button>
        </div>
        <div className="overflow-y-auto p-3 space-y-1.5">
          {loading && <p className="text-xs text-zinc-500">{t("loading")}</p>}
          {!loading && entries.length === 0 && <p className="text-xs text-zinc-500">{t("browse_empty")}</p>}
          {error && <p className="text-xs text-red-400">{error}</p>}
          {entries.map((e) => (
            <div key={e.source_rel} className="flex items-center gap-2 px-2 py-1.5 rounded bg-black/20 border border-white/5">
              <div className="min-w-0 flex-1">
                <p className="text-xs text-zinc-200 truncate">{e.filename}</p>
                <p className="text-[10px] text-zinc-500 truncate">{e.source_rel}</p>
              </div>
              {e.imported ? (
                <span className="text-[10px] text-emerald-400 flex-shrink-0">{t("already_imported")}</span>
              ) : (
                <button onClick={() => doImport(e)} disabled={importing === e.source_rel}
                  className="px-2 py-1 text-[11px] rounded bg-violet-500/15 border border-violet-500/30 text-violet-200 disabled:opacity-40 flex-shrink-0">
                  {importing === e.source_rel ? t("importing") : t("add")}
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
