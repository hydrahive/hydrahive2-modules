import { useCallback, useEffect, useRef, useState } from "react"
import type { Clip, VideoMeta } from "./types"
import { fileUrl, videoeditorApi } from "./api"
import { TimelineCanvas } from "./TimelineCanvas"

interface Props {
  projectId: string
  meta: VideoMeta
  onBack: () => void
}

function uid(): string {
  return "c" + Math.random().toString(36).slice(2, 10)
}

export function EditorView({ projectId, meta: initialMeta, onBack }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [meta, setMeta] = useState<VideoMeta>(initialMeta)
  const [playhead, setPlayhead] = useState(0)
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null)
  const [inPoint, setInPoint] = useState<number | null>(null)
  const [exporting, setExporting] = useState(false)
  const [saved, setSaved] = useState(true)

  const clips = meta.edl?.timeline ?? []

  const setClips = useCallback((next: Clip[]) => {
    setMeta((m) => ({ ...m, edl: { file_id: m.file_id, timeline: next } }))
    setSaved(false)
  }, [])

  function seek(t: number) {
    const v = videoRef.current
    if (v) v.currentTime = t
    setPlayhead(t)
  }

  // Video-Zeit → Playhead
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    const onTime = () => setPlayhead(v.currentTime)
    v.addEventListener("timeupdate", onTime)
    return () => v.removeEventListener("timeupdate", onTime)
  }, [])

  // Schnitt-Aktionen
  function markIn() { setInPoint(playhead) }
  function markOut() {
    if (inPoint === null || playhead <= inPoint) return
    setClips([...clips, { id: uid(), src_start: inPoint, src_end: playhead, mode: "reencode" }])
    setInPoint(null)
  }
  function splitAtPlayhead() {
    const target = clips.find((c) => playhead > c.src_start && playhead < c.src_end)
    if (!target) return
    setClips(clips.flatMap((c) => c.id !== target.id ? [c] : [
      { ...c, src_end: playhead },
      { id: uid(), src_start: playhead, src_end: c.src_end, mode: c.mode },
    ]))
  }
  function deleteSelected() {
    if (!selectedClipId) return
    setClips(clips.filter((c) => c.id !== selectedClipId))
    setSelectedClipId(null)
  }
  function trimClip(id: string, start: number, end: number) {
    setClips(clips.map((c) => c.id === id ? { ...c, src_start: start, src_end: end } : c))
  }
  function toggleMode(id: string) {
    setClips(clips.map((c) => c.id === id ? { ...c, mode: c.mode === "copy" ? "reencode" : "copy" } : c))
  }

  async function save() {
    await videoeditorApi.saveEdl(projectId, meta.file_id, { file_id: meta.file_id, timeline: clips })
    setSaved(true)
  }

  async function doExport() {
    await save()
    setExporting(true)
    try {
      const { job_id } = await videoeditorApi.startExport(projectId, meta.file_id, `${meta.filename}-schnitt.mp4`)
      // Job pollen
      for (let i = 0; i < 600; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const job = await videoeditorApi.getJob(projectId, job_id)
        if (job.status === "done") break
        if (job.status === "failed") throw new Error(job.error || "Export fehlgeschlagen")
      }
    } finally {
      setExporting(false)
    }
  }

  // Tastenkürzel
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === "INPUT") return
      if (e.key === "i") markIn()
      else if (e.key === "o") markOut()
      else if (e.key === "s") splitAtPlayhead()
      else if (e.key === "Delete" || e.key === "Backspace") deleteSelected()
      else if (e.key === " ") { e.preventDefault(); const v = videoRef.current; if (v) v.paused ? v.play() : v.pause() }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  })

  const selected = clips.find((c) => c.id === selectedClipId)

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <button onClick={onBack} className="px-2 py-1 text-xs rounded border border-white/10 text-zinc-300 hover:bg-white/5">← Bibliothek</button>
        <span className="text-sm text-zinc-200 font-medium truncate">{meta.filename}</span>
        <span className="text-[11px] text-zinc-500">{meta.width}×{meta.height} · {meta.fps}fps · {meta.duration.toFixed(1)}s</span>
        <span className="flex-1" />
        {!saved && <button onClick={save} className="px-2 py-1 text-xs rounded bg-sky-500/15 border border-sky-500/30 text-sky-200">Speichern</button>}
        <button onClick={doExport} disabled={exporting || clips.length === 0}
          className="px-3 py-1 text-xs rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 disabled:opacity-40">
          {exporting ? "Rendert…" : "Exportieren"}
        </button>
      </div>

      {meta.proxy_abs && (
        <video ref={videoRef} src={fileUrl(meta.proxy_abs)} controls
          className="w-full max-h-[45vh] bg-black rounded" />
      )}

      <div className="flex items-center gap-2 text-xs text-zinc-400">
        <button onClick={markIn} className="px-2 py-1 rounded border border-white/10 hover:bg-white/5">In (I)</button>
        <button onClick={markOut} disabled={inPoint === null} className="px-2 py-1 rounded border border-white/10 hover:bg-white/5 disabled:opacity-40">Out (O)</button>
        <button onClick={splitAtPlayhead} className="px-2 py-1 rounded border border-white/10 hover:bg-white/5">Split (S)</button>
        <button onClick={deleteSelected} disabled={!selectedClipId} className="px-2 py-1 rounded border border-white/10 hover:bg-white/5 disabled:opacity-40">Löschen</button>
        {inPoint !== null && <span className="text-amber-300">In @ {inPoint.toFixed(2)}s</span>}
        {selected && (
          <button onClick={() => toggleMode(selected.id)} className="px-2 py-1 rounded border border-white/10 hover:bg-white/5">
            Modus: {selected.mode === "copy" ? "Kopieren (schnell)" : "Neu kodieren"}
          </button>
        )}
        <span className="flex-1" />
        <span>Playhead {playhead.toFixed(2)}s · {clips.length} Clip(s)</span>
      </div>

      <TimelineCanvas
        meta={meta}
        playhead={playhead}
        selectedClipId={selectedClipId}
        onSeek={seek}
        onSelectClip={setSelectedClipId}
        onTrimClip={trimClip}
      />
    </div>
  )
}
