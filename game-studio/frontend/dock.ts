// Zustand des Agent-Docks (offen, Breite) im Browser merken, Breite begrenzen.
export const DOCK_KEY = "gameStudio.agentDock"
export const DOCK_MIN = 360
export const DOCK_DEFAULT = 480
export interface DockState { open: boolean; width: number }

export function clampWidth(width: number, viewport: number): number {
  const max = Math.max(DOCK_MIN, Math.floor(viewport * 0.6))
  if (!Number.isFinite(width)) return Math.min(DOCK_DEFAULT, max)
  return Math.min(max, Math.max(DOCK_MIN, Math.round(width)))
}

export function readDock(raw: string | null, viewport: number): DockState {
  try {
    const value = JSON.parse(raw ?? "") as Partial<DockState>
    return { open: value.open === true, width: clampWidth(typeof value.width === "number" ? value.width : DOCK_DEFAULT, viewport) }
  } catch {
    return { open: false, width: clampWidth(DOCK_DEFAULT, viewport) }
  }
}
