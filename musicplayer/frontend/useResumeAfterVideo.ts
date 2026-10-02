// Verdrahtung „Musik nach dem Video fortsetzen“ für die Video-Ansicht.
// Fortsetzen verzögert (RESUME_DELAY_MS): Chrome pausiert beim Spulen über die
// Zeitleiste kurz, ebenso beim Wechsel zum nächsten Video. Die Musik darf dabei
// nicht kurz anspringen. Die Entscheidung selbst steckt in mediaFocus.ts.
import { useCallback, useEffect, useRef, type RefObject } from "react"
import { forget, onVideoStart, shouldResume, type ResumeState } from "./mediaFocus"

export const RESUME_DELAY_MS = 300

export interface ResumeAfterVideo {
  onVideoPlay: () => void
  onVideoStop: () => void
  onPointerDown: () => void
  onPointerUp: () => void
  forget: () => void
}

export function useResumeAfterVideo(
  video: RefObject<HTMLVideoElement | null>,
  musicPlaying: boolean,
  pauseMusic: () => void,
  resumeMusic: () => void,
): ResumeAfterVideo {
  const state = useRef<ResumeState>(forget())
  const pointerDown = useRef(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Aktuelle Werte für Callbacks/Aufräumen, ohne sie bei jedem Render neu zu binden.
  const latest = useRef({ musicPlaying, pauseMusic, resumeMusic })
  useEffect(() => { latest.current = { musicPlaying, pauseMusic, resumeMusic } })

  const cancel = () => {
    if (timer.current !== null) clearTimeout(timer.current)
    timer.current = null
  }

  const tryResume = useCallback(() => {
    timer.current = null
    const v = video.current
    const moment = { videoPaused: !v || v.paused || v.ended, pointerDown: pointerDown.current }
    if (!shouldResume(state.current, moment)) return
    state.current = forget()
    latest.current.resumeMusic()
  }, [video])

  const onVideoPlay = useCallback(() => {
    cancel()
    state.current = onVideoStart(state.current, latest.current.musicPlaying)
    latest.current.pauseMusic()
  }, [])

  const onVideoStop = useCallback(() => {
    cancel()
    timer.current = setTimeout(tryResume, RESUME_DELAY_MS)
  }, [tryResume])

  const onPointerDown = useCallback(() => { pointerDown.current = true; cancel() }, [])
  const onPointerUp = useCallback(() => {
    pointerDown.current = false
    if (state.current.resume) onVideoStop()
  }, [onVideoStop])

  const forgetResume = useCallback(() => { cancel(); state.current = forget() }, [])

  // Ansicht wird verlassen (Wechsel zu Audio): Video verschwindet, Musik setzt fort.
  useEffect(() => () => {
    cancel()
    if (state.current.resume) latest.current.resumeMusic()
  }, [])

  return { onVideoPlay, onVideoStop, onPointerDown, onPointerUp, forget: forgetResume }
}
