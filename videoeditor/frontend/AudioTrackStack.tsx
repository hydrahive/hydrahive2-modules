import { useEffect, useRef } from "react"
import type { useEditorEdl } from "./useEditorEdl"
import { drawAudioTrack, AUDIO_ROW_H } from "./_audioDraw"
import type { ViewState } from "./_timelineDraw"
import { xAtTime } from "./_timelineDraw"
import { AudioTrackHeaders } from "./AudioTrackHeaders"
import { useAudioCanvas } from "./useAudioCanvas"
import { useAudioPeaks } from "./useAudioPeaks"

type Edl = ReturnType<typeof useEditorEdl>
type Sel = { trackId: string; clipId: string } | null

interface Props {
  projectId: string
  view: ViewState
  onViewChange: (updater: (v: ViewState) => ViewState) => void
  edl: Edl
  playhead: number
  selectedAudio: Sel
  onSelectAudio: (sel: Sel) => void
  hasVideoAudio: boolean
}

/** Mehrspur-Audio-Stack: Header-Spalte (links) + EIN Canvas über alle
 *  Track-Zeilen (rechts). Teilt sich ViewState mit der Video-Timeline, damit
 *  Zoom/Scroll synchron laufen. Waveform-Peaks werden lazy nachgeladen. */
export function AudioTrackStack(p: Props) {
  const { projectId, view, onViewChange, edl, playhead, selectedAudio, onSelectAudio } = p
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const tracks = edl.audioTracks
  const peaksByClipId = useAudioPeaks(projectId, tracks)
  const canvasH = tracks.length * AUDIO_ROW_H

  const handlers = useAudioCanvas({
    view, onViewChange, tracks, canvasRef, onSelectAudio,
    moveAudioClip: edl.moveAudioClip, trimAudioClip: edl.trimAudioClip,
  })

  // Canvas-Größe an Wrapper-Breite + Track-Anzahl anpassen und melden.
  useEffect(() => {
    const wrap = wrapRef.current
    const canvas = canvasRef.current
    if (!wrap || !canvas) return
    const measure = () => {
      const w = wrap.clientWidth
      const dpr = window.devicePixelRatio || 1
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(Math.max(1, canvasH) * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${Math.max(1, canvasH)}px`
      onViewChange((v) => (v.width === w ? v : { ...v, width: w }))
    }
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(wrap)
    return () => ro.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canvasH])

  // Re-Render bei jeder relevanten Zustandsänderung.
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || canvasH === 0) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    const dpr = window.devicePixelRatio || 1
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, view.width, canvasH)
    tracks.forEach((track, i) => {
      drawAudioTrack({
        ctx, v: view, y: i * AUDIO_ROW_H, track, peaksByClipId,
        selectedClipId: selectedAudio?.trackId === track.id ? selectedAudio.clipId : null,
        playhead,
      })
    })
    // Playhead über alle Zeilen
    const px = xAtTime(playhead, view)
    if (px >= 0 && px <= view.width) {
      ctx.strokeStyle = "#f472b6"; ctx.lineWidth = 1
      ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, canvasH); ctx.stroke()
    }
  }, [tracks, view, peaksByClipId, selectedAudio, playhead, canvasH])

  return (
    <div className="flex w-full rounded border border-white/10 overflow-hidden" style={{ background: "#07101a" }}>
      <AudioTrackHeaders
        originalAudio={edl.originalAudio}
        tracks={tracks}
        hasVideoAudio={p.hasVideoAudio}
        ops={{
          renameTrack: edl.renameTrack, removeTrack: edl.removeTrack,
          setTrackFlag: edl.setTrackFlag, setTrackGain: edl.setTrackGain,
          addTrack: () => edl.addTrack(), setOriginalAudio: edl.setOriginalAudio,
        }}
      />
      <div ref={wrapRef} className="flex-1 min-w-0 select-none border-l border-white/10">
        {/* Spacer korrespondierend zur O-Ton-Header-Zeile (kein Canvas nötig) */}
        <div className="border-b border-white/10 flex items-center px-2" style={{ height: AUDIO_ROW_H }}>
          <span className="text-[10px] text-zinc-600">Original-Tonspur (aus Video-Timeline)</span>
        </div>
        {canvasH > 0 ? (
          <canvas ref={canvasRef}
            onPointerDown={handlers.onPointerDown}
            onPointerMove={handlers.onPointerMove}
            onPointerUp={handlers.onPointerUp}
            onPointerCancel={handlers.onPointerUp}
            onWheel={handlers.onWheel}
            style={{ display: "block", cursor: "pointer" }} />
        ) : (
          <div className="flex items-center px-3 py-4 text-[11px] text-zinc-600" style={{ minHeight: 40 }}>
            Keine Audiospuren — „+ Audiospur" links oder „Audio hinzufügen" oben.
          </div>
        )}
      </div>
    </div>
  )
}
