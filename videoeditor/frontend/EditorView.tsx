import { useEffect, useRef, useState } from "react"
import type { VideoMeta } from "./types"
import { fileUrl } from "./api"
import { TimelineCanvas } from "./TimelineCanvas"
import { useEditorEdl } from "./useEditorEdl"
import { usePreview } from "./usePreview"
import { usePlayer } from "./usePlayer"
import { EditorToolbar } from "./EditorToolbar"
import { ExportDialog } from "./ExportDialog"

interface Props {
  projectId: string
  meta: VideoMeta
  onBack: () => void
}

export function EditorView({ projectId, meta, onBack }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null)
  const [inPoint, setInPoint] = useState<number | null>(null)
  const [showExport, setShowExport] = useState(false)

  const edl = useEditorEdl(projectId, meta)
  const preview = usePreview(
    (t) => player.seek(t),
    (play) => player.playPause(play),
  )
  const player = usePlayer(videoRef, meta.fps, meta.duration, edl.keyframes, preview.tick)

  const clips = edl.clips
  const selected = clips.find((c) => c.id === selectedClipId)

  // ---- Schnitt-Aktionen ----
  function markIn() { setInPoint(player.playhead) }
  function markOut() {
    if (inPoint === null || player.playhead <= inPoint) return
    const id = edl.addRange(inPoint, player.playhead)
    if (id) setSelectedClipId(id)
    setInPoint(null)
  }
  function split() {
    const id = edl.splitAt(player.playhead)
    if (id) setSelectedClipId(id)
  }
  function del() {
    if (!selectedClipId) return
    edl.remove(selectedClipId)
    setSelectedClipId(null)
  }

  // ---- Tastenkürzel ----
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === "INPUT") return
      const mod = e.ctrlKey || e.metaKey
      if (mod && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? edl.redo() : edl.undo(); return }
      if (mod && e.key.toLowerCase() === "y") { e.preventDefault(); edl.redo(); return }
      switch (e.key) {
        case "i": markIn(); break
        case "o": markOut(); break
        case "s": split(); break
        case "Delete": case "Backspace": del(); break
        case " ": e.preventDefault(); player.togglePlay(); break
        case "ArrowLeft": e.preventDefault(); player.stepFrame(e.shiftKey ? -10 : -1); break
        case "ArrowRight": e.preventDefault(); player.stepFrame(e.shiftKey ? 10 : 1); break
        case "j": player.nudge(-10); break
        case "l": player.nudge(10); break
        case "[": player.jumpPrevKeyframe(); break
        case "]": player.jumpNextKeyframe(); break
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  })

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <button onClick={onBack} className="px-2 py-1 text-xs rounded border border-white/10 text-zinc-300 hover:bg-white/5">← Bibliothek</button>
        <span className="text-sm text-zinc-200 font-medium truncate">{meta.filename}</span>
        <span className="text-[11px] text-zinc-500">{meta.width}×{meta.height} · {meta.fps}fps · {meta.duration.toFixed(1)}s</span>
        <span className="flex-1" />
        <span className="text-[11px] text-zinc-500">{edl.saved ? "gespeichert" : "…"}</span>
        <button onClick={() => setShowExport(true)} disabled={clips.length === 0}
          className="px-3 py-1 text-xs rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 disabled:opacity-40">
          Exportieren
        </button>
      </div>

      {meta.proxy_abs && (
        <video ref={videoRef} src={fileUrl(meta.proxy_abs)}
          className="w-full max-h-[45vh] bg-black rounded" onClick={player.togglePlay} />
      )}

      <EditorToolbar
        player={player} edl={edl} preview={preview}
        inPoint={inPoint} selected={selected} clips={clips}
        onMarkIn={markIn} onMarkOut={markOut} onSplit={split} onDelete={del}
        selectedClipId={selectedClipId}
      />

      <TimelineCanvas
        meta={{ ...meta, edl: { file_id: meta.file_id, timeline: clips } }}
        playhead={player.playhead}
        selectedClipId={selectedClipId}
        playingClipId={preview.playingClipId}
        onSeek={player.seek}
        onSelectClip={setSelectedClipId}
        onTrimClip={edl.trim}
      />

      {showExport && (
        <ExportDialog
          projectId={projectId} fileId={meta.file_id} filename={meta.filename}
          onClose={() => setShowExport(false)} onSaveFirst={edl.saveNow}
        />
      )}
    </div>
  )
}
