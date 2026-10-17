import { useCallback, useEffect, useState } from "react"
import type { LibraryItem } from "./api"
import { DEMO_DURATION } from "./demoData"
import { loadLayout, saveLayout, dragLayout, type StudioLayout } from "./layout"
import { actionFor, type ShortcutAction } from "./shortcuts"
import { clampViewport, type Viewport } from "./timeline"
import { usePlayer } from "./usePlayer"
import type { Workspace } from "./workspaces"

const FPS = 25

/** Abspielsteuerung, die die Tasten übernimmt (z. B. der Film im Reiter „Schneiden“). */
export interface Transport {
  time: number
  total: number
  seek: (t: number) => void
  toggle: () => void
  shuttle: (dir: 1 | -1) => void
}

/** Zustand des Studios: Auswahl, echtes Medium in der Vorschau (Etappe 1), Demo-Zeitleiste, Layout, Dialoge, Tasten. */
export function useStudioState(items: LibraryItem[], workspace: Workspace, setWorkspace: (w: Workspace) => void,
  transport: (item: LibraryItem | null) => Transport | null) {
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
  const tr = transport(item)                          // Film im Reiter „Schneiden“ hat Vorrang vor der Demo

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
    const end = tr ? tr.total : item ? player.duration : DEMO_DURATION
    const now = tr ? tr.time : time
    const go = tr ? tr.seek : seek
    const map: Partial<Record<ShortcutAction, () => void>> = {
      "toggle-play": () => (tr ? tr.toggle() : player.toggle()),
      "seek-back": () => (tr ? tr.shuttle(-1) : player.shuttle(-1)), "seek-forward": () => (tr ? tr.shuttle(1) : player.shuttle(1)),
      "frame-back": () => go(now - 1 / FPS), "frame-forward": () => go(now + 1 / FPS),
      "jump-back": () => go(now - 5), "jump-forward": () => go(now + 5),
      "goto-start": () => go(0), "goto-end": () => go(end),
      "toggle-snap": () => setSnap((s) => !s),
      help: () => setDialog("help"), command: () => setDialog("command"),
    }
    const fn = map[a]
    if (fn) fn()
    else setToast(a)                                  // Bearbeiten kommt mit dem Schnitt (Etappe 4)
  }, [item, player, seek, time, tr])

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
