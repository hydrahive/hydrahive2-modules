import { useEffect, useRef, useState } from "react"
import type { AudioBrowseEntry, AudioMeta, VideoMeta } from "./types"
import { fileUrl } from "./api"
import { TimelineCanvas } from "./TimelineCanvas"
import { AudioTrackStack } from "./AudioTrackStack"
import { AudioLibraryPanel } from "./AudioLibraryPanel"
import { AudioClipInspector } from "./AudioClipInspector"
import { useEditorEdl } from "./useEditorEdl"
import { usePreview } from "./usePreview"
import { usePlayer } from "./usePlayer"
import { EditorToolbar } from "./EditorToolbar"
import { ExportDialog } from "./ExportDialog"
import type { ViewState } from "./_timelineDraw"

interface Props {
  projectId: string
  meta: VideoMeta
  onBack: () => void
}

type AudioSel = { trackId: string; clipId: string } | null

export function EditorView({ projectId, meta, onBack }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null)
  const [inPoint, setInPoint] = useState<number | null>(null)
  const [showExport, setShowExport] = useState(false)
  const [showAudioLib, setShowAudioLib] = useState(false)
  const [selectedAudio, setSelectedAudio] = useState<AudioSel>(null)
  const [view, setView] = useState<ViewState>({ pxPerSec: 40, scrollX: 0, width: 800 })

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

  // ---- Audio einfügen ----
  // addTrack() liefert keine id zurück → bei leerem Stack legen wir eine Spur
  // an und führen den Insert im nächsten Render aus (pendingInsert), sobald
  // die neue Spur im State sichtbar ist. Bei vorhandenen Spuren: letzte Spur.
  const pendingInsert = useRef<{ sourceRel: string; duration: number } | null>(null)

  useEffect(() => {
    const pending = pendingInsert.current
    if (!pending) return
    const track = edl.audioTracks[edl.audioTracks.length - 1]
    if (!track) return
    pendingInsert.current = null
    edl.addAudioClip(track.id, pending.sourceRel, player.playhead, pending.duration)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [edl.audioTracks])

  function onInsertAudio(entry: AudioBrowseEntry, meta: AudioMeta) {
    const track = edl.audioTracks[edl.audioTracks.length - 1]
    if (track) {
      edl.addAudioClip(track.id, entry.source_rel, player.playhead, meta.duration)
    } else {
      // Kein Track vorhanden → anlegen, Insert im Folge-Render nachziehen.
      pendingInsert.current = { sourceRel: entry.source_rel, duration: meta.duration }
      edl.addTrack()
    }
    setShowAudioLib(false)
  }

  // ---- Audio-Clip-Inspector-Daten ----
  const audioSelData = (() => {
    if (!selectedAudio) return null
    const track = edl.audioTracks.find((t) => t.id === selectedAudio.trackId)
    const clip = track?.clips.find((c) => c.id === selectedAudio.clipId)
    return clip ? { trackId: selectedAudio.trackId, clip } : null
  })()

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
        <button onClick={() => setShowAudioLib(true)}
          className="px-3 py-1 text-xs rounded bg-cyan-500/15 border border-cyan-500/30 text-cyan-200">
          Audio hinzufügen
        </button>
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
        view={view}
        onViewChange={setView}
        onSeek={player.seek}
        onSelectClip={setSelectedClipId}
        onTrimClip={edl.trim}
      />

      <AudioTrackStack
        projectId={projectId}
        view={view}
        onViewChange={setView}
        edl={edl}
        playhead={player.playhead}
        selectedAudio={selectedAudio}
        onSelectAudio={setSelectedAudio}
        hasVideoAudio={meta.has_audio}
      />

      {audioSelData && (
        <AudioClipInspector
          clip={audioSelData.clip}
          onGain={(db) => edl.setClipGain(audioSelData.trackId, audioSelData.clip.id, db)}
          onFade={(fade) => edl.setClipFade(audioSelData.trackId, audioSelData.clip.id, fade)}
          onSplit={() => edl.splitAudioClipAt(audioSelData.trackId, audioSelData.clip.id, player.playhead)}
          onRemove={() => { edl.removeAudioClip(audioSelData.trackId, audioSelData.clip.id); setSelectedAudio(null) }}
          onClose={() => setSelectedAudio(null)}
        />
      )}

      {showAudioLib && (
        <AudioLibraryPanel
          projectId={projectId}
          onClose={() => setShowAudioLib(false)}
          onInsert={onInsertAudio}
        />
      )}

      {showExport && (
        <ExportDialog
          projectId={projectId} fileId={meta.file_id} filename={meta.filename}
          onClose={() => setShowExport(false)} onSaveFirst={edl.saveNow}
        />
      )}
    </div>
  )
}
