// Ghostwriter G4e – Zustand des Chat-Fensters (offen, Breite) im Browser merken; Strg/Cmd+Shift+K schaltet um.
import { useCallback, useEffect, useState } from "react"
import { clampWidth, DOCK_KEY, readDock, type DockState } from "./chatDock"

export function useChatDock(enabled: boolean) {
  const [dock, setDock] = useState<DockState>(() => readDock(localStorage.getItem(DOCK_KEY), window.innerWidth))
  useEffect(() => { localStorage.setItem(DOCK_KEY, JSON.stringify(dock)) }, [dock])
  const toggle = useCallback(() => setDock((d) => ({ ...d, open: !d.open })), [])
  useEffect(() => {
    if (!enabled) return
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "k") { e.preventDefault(); toggle() }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [enabled, toggle])
  return {
    open: enabled && dock.open, width: dock.width, toggle,
    show: useCallback(() => setDock((d) => ({ ...d, open: true })), []),
    close: useCallback(() => setDock((d) => ({ ...d, open: false })), []),
    setWidth: useCallback((w: number) => setDock((d) => ({ ...d, width: clampWidth(w, window.innerWidth) })), []),
  }
}
