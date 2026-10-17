import { useCallback, useEffect, useState } from "react"
import type { LibraryItem } from "./api"
import { DEMO_DURATION } from "./demoData"
import { loadLayout, saveLayout, dragLayout, type StudioLayout } from "./layout"
import { actionFor, type ShortcutAction } from "./shortcuts"
import { clampViewport, type Viewport } from "./timeline"
import { usePlayer } from "./usePlayer"
import type { Workspace } from "./workspaces"

const FPS = 25

/** Zustand des Studios: Auswahl, echtes Medium in der Vorschau (Etappe 1), Demo-Zeitleiste, Layout, Dialoge, Tasten. */
export function useStudioState(items: LibraryItem[]) {
  const [workspace, setWorkspace] = useState<Workspace>("edit")
  const [demoTime, setDemoTime] = useState(8)
  const [manualView, setView] = useState<Viewport>({ start: 0, span: 40 })
  const [snap, setSnap] = useState(true)
  const [clipId, setClipId] = useState<string | null>(null)
  const [mediaId, setMediaId] = useState<string | null>(null)
  const [layout, setLayout] = useState<StudioLayout>(() => loadLayout())
  const [dialog, setDialog] = useState<"help" | "command" | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const item = items.find((i) => i.id === mediaId) ?? null
  const player = usePlayer(item?.id ?? null)

  useEffect(() => { saveLayout(layout) }, [layout])

  // Demo-Zeitleiste: Abspielkopf folgt dem Medium, solange eines läuft; sonst bleibt er stehen.
  const time = item ? player.time : demoTime
  const outside = time < manualView.start || time > manualView.start + manualView.span
  const view = outside ? clampViewport({ start: time - manualView.span * 0.2, span: manualView.span }, DEMO_DURATION) : manualView

  const seek = useCallback((t: number) => {
    if (item) player.seek(t)
    else setDemoTime(Math.min(DEMO_DURATION, Math.max(0, t)))
  }, [item, player])

  const run = useCallback((a: ShortcutAction) => {
    const end = item ? player.duration : DEMO_DURATION
    const map: Partial<Record<ShortcutAction, () => void>> = {
      "toggle-play": () => player.toggle(),
      "seek-back": () => player.shuttle(-1), "seek-forward": () => player.shuttle(1),
      "frame-back": () => seek(time - 1 / FPS), "frame-forward": () => seek(time + 1 / FPS),
      "jump-back": () => seek(time - 5), "jump-forward": () => seek(time + 5),
      "goto-start": () => seek(0), "goto-end": () => seek(end),
      "toggle-snap": () => setSnap((s) => !s),
      help: () => setDialog("help"), command: () => setDialog("command"),
    }
    const fn = map[a]
    if (fn) fn()
    else setToast(a)                                  // Bearbeiten kommt mit dem Schnitt (Etappe 4)
  }, [item, player, seek, time])

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
    workspace, setWorkspace, item, player, time, seek, view, setView, snap,
    toggleSnap: () => setSnap((s) => !s), clipId, selectClip: (id: string) => { setClipId(id); setMediaId(null) },
    mediaId, selectMedia: (id: string) => { setMediaId(id); setClipId(null) }, clearMedia: () => setMediaId(null), layout,
    drag: (key: keyof StudioLayout, d: number) => setLayout((l) => dragLayout(l, key, d)),
    dialog, setDialog, run, toast,
  }
}
