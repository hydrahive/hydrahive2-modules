import { useCallback, useEffect, useState } from "react"
import type { LibraryItem } from "./api"
import { loadLayout, saveLayout, dragLayout, type StudioLayout } from "./layout"
import { actionFor, type ShortcutAction } from "./shortcuts"
import { usePlayer } from "./usePlayer"
import type { Workspace } from "./workspaces"
import { firstVisit } from "./guideLogic"

const FPS = 25

/** Steuerung, die die Tasten übernimmt (z. B. der Film im Reiter „Schneiden“). Ohne Abspielteil bleiben
 *  Abspieltasten beim gewählten Medium. */
export interface Transport {
  time?: number
  total?: number
  seek?: (t: number) => void
  toggle?: () => void
  shuttle?: (dir: 1 | -1) => void
  /** Bearbeitungstasten (Teilen, Löschen, Rückgängig …); true = übernommen. */
  edit?: (a: ShortcutAction) => boolean
  toggleSnap?: () => void
}

/** Zustand des Studios: Arbeitsbereich, gewähltes Medium in der Vorschau, Layout, Dialoge, Tasten. */
export function useStudioState(items: LibraryItem[], workspace: Workspace, setWorkspace: (w: Workspace) => void,
  transport: (item: LibraryItem | null) => Transport | null) {
  const [snap, setSnap] = useState(true)
  const [mediaId, setMediaId] = useState<string | null>(null)
  const [layout, setLayout] = useState<StudioLayout>(() => loadLayout())
  const [dialog, setDialog] = useState<"help" | "command" | null>(() => (firstVisit() ? "help" : null))   // C3: erster Besuch → Hilfe
  const [toast, setToast] = useState<string | null>(null)

  const item = items.find((i) => i.id === mediaId) ?? null
  const player = usePlayer(item?.id ?? null)
  const tr = transport(item)                          // Film im Reiter „Schneiden“ hat Vorrang

  useEffect(() => { saveLayout(layout) }, [layout])

  const time = item ? player.time : 0
  const seek = useCallback((t: number) => { if (item) player.seek(t) }, [item, player])

  const run = useCallback((a: ShortcutAction) => {
    const film = tr?.seek && tr.toggle && tr.shuttle ? tr : null
    const end = film ? film.total ?? 0 : player.duration
    const now = film ? film.time ?? 0 : time
    const go = film?.seek ?? seek
    const map: Partial<Record<ShortcutAction, () => void>> = {
      "toggle-play": () => (film?.toggle ? film.toggle() : player.toggle()),
      "seek-back": () => (film?.shuttle ? film.shuttle(-1) : player.shuttle(-1)),
      "seek-forward": () => (film?.shuttle ? film.shuttle(1) : player.shuttle(1)),
      "frame-back": () => go(now - 1 / FPS), "frame-forward": () => go(now + 1 / FPS),
      "jump-back": () => go(now - 5), "jump-forward": () => go(now + 5),
      "goto-start": () => go(0), "goto-end": () => go(end),
      "toggle-snap": () => (tr?.toggleSnap ? tr.toggleSnap() : setSnap((s) => !s)),
      help: () => setDialog("help"), command: () => setDialog("command"),
    }
    const fn = map[a]
    if (fn) fn()
    else if (!tr?.edit?.(a)) setToast(a)              // außerhalb von „Schneiden“ bzw. Marker: kommt später
  }, [player, seek, time, tr])

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
    workspace, setWorkspace, item, player, time, seek, snap,
    mediaId, selectMedia: (id: string) => setMediaId(id), clearMedia: () => setMediaId(null), layout,
    drag: (key: keyof StudioLayout, d: number) => setLayout((l) => dragLayout(l, key, d)),
    dialog, setDialog, run, toast,
  }
}
