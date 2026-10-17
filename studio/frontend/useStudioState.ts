import { useCallback, useEffect, useState } from "react"
import { DEMO_DURATION } from "./demoData"
import { loadLayout, saveLayout, dragLayout, type StudioLayout } from "./layout"
import { actionFor, type ShortcutAction } from "./shortcuts"
import type { Workspace } from "./workspaces"
import { clampViewport, type Viewport } from "./timeline"

const FPS = 25

/** Zustand der Attrappe: Abspielkopf, Wiedergabe, Ausschnitt, Auswahl, Layout, Dialoge, Tastenkürzel. */
export function useStudioState() {
  const [workspace, setWorkspace] = useState<Workspace>("edit")
  const [time, setTimeRaw] = useState(8)
  const [playing, setPlaying] = useState(false)
  const [rate, setRate] = useState(1)
  const [manualView, setView] = useState<Viewport>({ start: 0, span: 40 })
  const [snap, setSnap] = useState(true)
  const [clipId, setClipId] = useState<string | null>(null)
  const [mediaId, setMediaId] = useState<string | null>(null)
  const [layout, setLayout] = useState<StudioLayout>(() => loadLayout())
  const [dialog, setDialog] = useState<"help" | "command" | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const setTime = useCallback((t: number) => setTimeRaw(Math.min(DEMO_DURATION, Math.max(0, t))), [])

  useEffect(() => {
    if (!playing) return
    const id = window.setInterval(() => setTimeRaw((t) => {
      const next = t + rate / FPS
      if (next >= DEMO_DURATION || next <= 0) { setPlaying(false); return Math.min(DEMO_DURATION, Math.max(0, next)) }
      return next
    }), 1000 / FPS)
    return () => window.clearInterval(id)
  }, [playing, rate])

  useEffect(() => { saveLayout(layout) }, [layout])

  // Abspielkopf bleibt im Ausschnitt sichtbar: läuft er hinaus, rückt der Ausschnitt mit (ohne extra Render).
  const outside = time < manualView.start || time > manualView.start + manualView.span
  const view = outside ? clampViewport({ start: time - manualView.span * 0.2, span: manualView.span }, DEMO_DURATION) : manualView

  const run = useCallback((a: ShortcutAction) => {
    const shuttle = (dir: 1 | -1) => {
      setRate((r) => (Math.sign(r) === dir && playing ? Math.min(Math.abs(r) * 2, 8) * dir : dir))
      setPlaying(true)
    }
    const map: Partial<Record<ShortcutAction, () => void>> = {
      "toggle-play": () => { setRate(1); setPlaying((p) => !p) },
      "seek-back": () => shuttle(-1), "seek-forward": () => shuttle(1),
      "frame-back": () => { setPlaying(false); setTime(time - 1 / FPS) }, "frame-forward": () => { setPlaying(false); setTime(time + 1 / FPS) },
      "jump-back": () => setTime(time - 5), "jump-forward": () => setTime(time + 5),
      "goto-start": () => setTime(0), "goto-end": () => setTime(DEMO_DURATION),
      "toggle-snap": () => setSnap((s) => !s),
      help: () => setDialog("help"), command: () => setDialog("command"),
    }
    const fn = map[a]
    if (fn) fn()
    else setToast(a)                                  // Attrappe: Bearbeiten kommt ab Etappe 2
  }, [playing, setTime, time])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (dialog) return
      const a = actionFor(e, e.target)
      if (!a) return
      e.preventDefault()
      run(a)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [dialog, run])

  useEffect(() => {
    if (!toast) return
    const id = window.setTimeout(() => setToast(null), 1800)
    return () => window.clearTimeout(id)
  }, [toast])

  return {
    workspace, setWorkspace, time, setTime, playing, togglePlay: () => run("toggle-play"), view, setView, snap,
    toggleSnap: () => setSnap((s) => !s), clipId, selectClip: (id: string) => { setClipId(id); setMediaId(null) },
    mediaId, selectMedia: (id: string) => { setMediaId(id); setClipId(null) }, layout,
    drag: (key: keyof StudioLayout, d: number) => setLayout((l) => dragLayout(l, key, d)),
    dialog, setDialog, run, toast,
  }
}
