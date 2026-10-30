import { useEffect, useState } from "react"
import type { AudioBrowseEntry, AudioMeta } from "./types"
import { videoeditorApi } from "./api"

interface Props {
  projectId: string
  onClose: () => void
  onInsert: (entry: AudioBrowseEntry, meta: AudioMeta) => void
}

/** Dialog: Audioquellen im Projekt-Workspace — aufbereiten (Peaks/Decode)
 *  und in die Tonspur einfügen. Kein Silo: alles bleibt im Workspace. */
export function AudioLibraryPanel({ projectId, onClose, onInsert }: Props) {
  const [entries, setEntries] = useState<AudioBrowseEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [inserted, setInserted] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    videoeditorApi.audioBrowse(projectId)
      .then(setEntries)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [projectId])

  async function doPrepare(entry: AudioBrowseEntry) {
    setBusy(entry.source_rel); setError(null)
    try {
      const { job_id } = await videoeditorApi.audioPrepare(projectId, entry.source_rel)
      for (let i = 0; i < 300; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const job = await videoeditorApi.getJob(projectId, job_id)
        if (job.status === "done") break
        if (job.status === "failed") throw new Error(job.error || "Aufbereitung fehlgeschlagen")
      }
      setEntries((es) => es.map((e) =>
        e.source_rel === entry.source_rel ? { ...e, prepared: true } : e))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(null)
    }
  }

  async function doInsert(entry: AudioBrowseEntry) {
    setBusy(entry.source_rel); setError(null)
    try {
      const meta = await videoeditorApi.audioMeta(projectId, entry.audio_id)
      onInsert(entry, meta)
      setInserted(entry.source_rel)
      setTimeout(() => setInserted((cur) => (cur === entry.source_rel ? null : cur)), 1500)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="w-full max-w-lg max-h-[80vh] flex flex-col rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[rgb(var(--hh-s-rand,42_54_75))]">
          <p className="text-sm font-semibold text-[#e8eef8]">Audio-Bibliothek</p>
          <button onClick={onClose} className="text-[#9aa7bc] hover:text-[#e8eef8]">✕</button>
        </div>
        <div className="overflow-y-auto p-3 space-y-1.5">
          {loading && <p className="text-xs text-[#9aa7bc]">Lade…</p>}
          {!loading && entries.length === 0 && (
            <p className="text-xs text-[#9aa7bc]">Keine Audioquellen im Projekt.</p>
          )}
          {error && <p className="text-xs text-red-400">{error}</p>}
          {entries.map((e) => (
            <div key={e.source_rel}
              className="flex items-center gap-2 px-2 py-1.5 rounded bg-black/20 border border-[rgb(var(--hh-s-rand,42_54_75))]">
              <div className="min-w-0 flex-1">
                <p className="text-xs text-[#e8eef8] truncate">{e.filename}</p>
                <p className="text-[10px] text-[#9aa7bc] truncate">{e.source_rel}</p>
              </div>
              {inserted === e.source_rel && (
                <span className="text-[10px] text-emerald-400 flex-shrink-0">eingefügt</span>
              )}
              {e.prepared ? (
                <button onClick={() => doInsert(e)} disabled={busy === e.source_rel}
                  className="px-2 py-1 text-[11px] rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 disabled:opacity-40 flex-shrink-0">
                  Einfügen
                </button>
              ) : (
                <button onClick={() => doPrepare(e)} disabled={busy === e.source_rel}
                  className="px-2 py-1 text-[11px] rounded bg-cyan-500/15 border border-cyan-500/30 text-cyan-200 disabled:opacity-40 flex-shrink-0">
                  {busy === e.source_rel ? "Aufbereiten…" : "Aufbereiten"}
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
