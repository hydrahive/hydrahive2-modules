import { useEffect, useState } from "react"
import { ModalPortal } from "@/shared/ModalPortal"
import type { RenderPreset } from "./types"
import { videoeditorApi } from "./api"

interface Props {
  projectId: string
  fileId: string
  filename: string
  onClose: () => void
  onSaveFirst: () => Promise<void>
}

type Phase = "choose" | "running" | "done" | "failed"

export function ExportDialog({ projectId, fileId, filename, onClose, onSaveFirst }: Props) {
  const [presets, setPresets] = useState<RenderPreset[]>([])
  const [presetId, setPresetId] = useState("passthrough")
  const [phase, setPhase] = useState<Phase>("choose")
  const [percent, setPercent] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    videoeditorApi.presets().then(setPresets).catch(() => {})
  }, [])

  async function start() {
    setError(null); setPhase("running"); setPercent(0)
    try {
      await onSaveFirst()
      const { job_id } = await videoeditorApi.startExport(projectId, fileId, `${filename}-schnitt.mp4`, presetId)
      for (let i = 0; i < 1800; i++) {
        await new Promise((r) => setTimeout(r, 1500))
        const job = await videoeditorApi.getJob(projectId, job_id)
        setPercent(job.percent ?? 0)
        if (job.status === "done") { setPhase("done"); setPercent(100); return }
        if (job.status === "failed") throw new Error(job.error || "Export fehlgeschlagen")
      }
      throw new Error("Zeitüberschreitung")
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setPhase("failed")
    }
  }

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={(e) => { if (e.target === e.currentTarget && phase !== "running") onClose() }}>
      <div className="w-full max-w-md rounded-lg border border-white/10 bg-zinc-900 p-5 space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-zinc-100">Exportieren</p>
          {phase !== "running" && <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200">✕</button>}
        </div>

        {phase === "choose" && (
          <>
            <div className="space-y-1.5">
              {presets.map((p) => (
                <label key={p.id}
                  className={`flex items-start gap-2 p-2 rounded border cursor-pointer ${presetId === p.id ? "border-violet-500/50 bg-violet-500/10" : "border-white/10 hover:bg-white/5"}`}>
                  <input type="radio" name="preset" checked={presetId === p.id}
                    onChange={() => setPresetId(p.id)} className="mt-1" />
                  <div>
                    <p className="text-xs text-zinc-100 font-medium">{p.title}</p>
                    <p className="text-[10px] text-zinc-500">{p.note}</p>
                  </div>
                </label>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={onClose} className="px-3 py-1.5 text-xs rounded border border-white/10 text-zinc-400 hover:bg-white/5">Abbrechen</button>
              <button onClick={start} className="px-3 py-1.5 text-xs rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-200">Rendern</button>
            </div>
          </>
        )}

        {phase === "running" && (
          <div className="space-y-2">
            <p className="text-xs text-zinc-300">Rendert… {percent}%</p>
            <div className="h-2 rounded bg-black/40 overflow-hidden">
              <div className="h-full bg-emerald-500 transition-all" style={{ width: `${percent}%` }} />
            </div>
          </div>
        )}

        {phase === "done" && (
          <div className="space-y-3">
            <p className="text-xs text-emerald-300">✓ Export fertig — liegt im Projekt unter videoeditor/exports/</p>
            <div className="flex justify-end"><button onClick={onClose} className="px-3 py-1.5 text-xs rounded bg-white/[6%] border border-white/10 text-zinc-200">Schließen</button></div>
          </div>
        )}

        {phase === "failed" && (
          <div className="space-y-3">
            <p className="text-xs text-red-400">{error}</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setPhase("choose")} className="px-3 py-1.5 text-xs rounded border border-white/10 text-zinc-300 hover:bg-white/5">Zurück</button>
              <button onClick={onClose} className="px-3 py-1.5 text-xs rounded bg-white/[6%] border border-white/10 text-zinc-200">Schließen</button>
            </div>
          </div>
        )}
      </div>
    </div>
    </ModalPortal>
  )
}
