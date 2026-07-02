import { useCallback, useRef, useState } from "react"
import type { Clip } from "./types"

type Preview =
  | { kind: "range"; start: number; end: number }
  | { kind: "clip"; clipId: string; start: number; end: number }
  | { kind: "timeline"; clips: Clip[]; index: number; start: number; end: number }
  | null

/** Preview-Playback OHNE Rendern: spielt einen Bereich, einen einzelnen Clip
 *  oder die ganze zusammengeschnittene EDL ab, indem der Player von Clip zu
 *  Clip springt. Der Player ruft tick(t) bei jedem timeupdate — Rückgabe sagt
 *  ihm, ob er springen (seekTo) oder stoppen (stop) soll. */
export function usePreview(seek: (t: number) => void, playPause: (play: boolean) => void) {
  const [preview, setPreview] = useState<Preview>(null)
  const [playingClipId, setPlayingClipId] = useState<string | null>(null)
  const previewRef = useRef<Preview>(null)
  previewRef.current = preview

  const stop = useCallback(() => {
    setPreview(null)
    setPlayingClipId(null)
  }, [])

  const playRange = useCallback((start: number, end: number) => {
    if (end <= start) return
    setPreview({ kind: "range", start, end })
    setPlayingClipId(null)
    seek(start)
    playPause(true)
  }, [seek, playPause])

  const playClip = useCallback((clip: Clip) => {
    setPreview({ kind: "clip", clipId: clip.id, start: clip.src_start, end: clip.src_end })
    setPlayingClipId(clip.id)
    seek(clip.src_start)
    playPause(true)
  }, [seek, playPause])

  const playTimeline = useCallback((clips: Clip[]) => {
    if (!clips.length) return
    const tl = [...clips].sort((a, b) => a.src_start - b.src_start)
    setPreview({ kind: "timeline", clips: tl, index: 0, start: tl[0].src_start, end: tl[0].src_end })
    setPlayingClipId(tl[0].id)
    seek(tl[0].src_start)
    playPause(true)
  }, [seek, playPause])

  /** Vom Player bei jedem timeupdate aufgerufen. */
  const tick = useCallback((t: number) => {
    const p = previewRef.current
    if (!p) return
    if (t < p.end - 0.02) return

    if (p.kind === "timeline") {
      const next = p.index + 1
      if (next < p.clips.length) {
        const c = p.clips[next]
        const np: Preview = { kind: "timeline", clips: p.clips, index: next, start: c.src_start, end: c.src_end }
        setPreview(np)
        setPlayingClipId(c.id)
        seek(c.src_start)
        playPause(true)
        return
      }
    }
    // range/clip Ende, oder Timeline durch → stoppen
    playPause(false)
    stop()
  }, [seek, playPause, stop])

  return { preview, playingClipId, playRange, playClip, playTimeline, stop, tick, isPreviewing: preview !== null }
}
