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
      <div className="w-full max-w-lg max-h-[80vh] flex flex-col rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[rgb(var(--hh-s-rand,42_54_75))]">
          <p className="text-sm font-semibold text-[#e8eef8]">{t("browse_title")}</p>
          <button onClick={onClose} className="text-[#9aa7bc] hover:text-[#e8eef8]">✕</button>
        </div>
        <div className="overflow-y-auto p-3 space-y-1.5">
          {loading && <p className="text-xs text-[#9aa7bc]">{t("loading")}</p>}
          {!loading && entries.length === 0 && <p className="text-xs text-[#9aa7bc]">{t("browse_empty")}</p>}
          {error && <p className="text-xs text-red-400">{error}</p>}
          {entries.map((e) => (
            <div key={e.source_rel} className="flex items-center gap-2 px-2 py-1.5 rounded bg-black/20 border border-[rgb(var(--hh-s-rand,42_54_75))]">
              <div className="min-w-0 flex-1">
                <p className="text-xs text-[#e8eef8] truncate">{e.filename}</p>
                <p className="text-[10px] text-[#9aa7bc] truncate">{e.source_rel}</p>
              </div>
              {e.imported ? (
                <span className="text-[10px] text-emerald-400 flex-shrink-0">{t("already_imported")}</span>
              ) : (
                <button onClick={() => doImport(e)} disabled={importing === e.source_rel}
                  className="px-2 py-1 text-[11px] rounded bg-[#69d7ff]/15 border border-[#69d7ff]/30 text-[#69d7ff] disabled:opacity-40 flex-shrink-0">
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
